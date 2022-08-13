# -*- coding: utf-8 -*-
"""
Created on Fri Jun 24 16:55:19 2022

@author: svc_ccg
"""

import os
import sys
import time
import numpy as np
from scipy.ndimage import gaussian_filter
from sklearn.model_selection import KFold
import matplotlib
import matplotlib.pyplot as plt
matplotlib.rcParams['pdf.fonttype'] = 42
import fileIO
from DynamicRoutingAnalysisUtils import DynRoutData,sortExps
import psytrack
from glmhmm import glm_hmm
from glmhmm.utils import permute_states, find_best_fit, compare_top_weights
from glmhmm.visualize import plot_model_params, plot_loglikelihoods, plot_weights



# Ethan's mice
# 594825 – 4/11-4/15
# 596921 – 3/29-4/1
# 589583 – 4/05-4/11
# 588997 – 3/9-3/15

# Sam's mice
# 594530:  2/25,28; 3/1-4
# 596919:  2/25,28; 3/1
# 596926:  2/25,28: 3/1,9,11
# 610739:  3/2-4,7-9

behavDir = r"\\allen\programs\mindscope\workgroups\dynamicrouting\DynamicRoutingTask"
behavFiles = []
while True:
    files = fileIO.getFiles('choose experiments',rootDir=os.path.join(behavDir,'Data'),fileType='*.hdf5')
    if len(files)>0:
        behavFiles.extend(files)
    else:
        break
    
if len(behavFiles)>0:
    exps = []
    for f in behavFiles:
        obj = DynRoutData()
        obj.loadBehavData(f)
        exps.append(obj)
        
exps = sortExps(exps)


exps = handoffSessions


regressors = ['model','attention','reinforcement','persistence','bias']
regressorColors = 'rbgcy'
x = {r: [] for r in regressors}
y = []
sessionTrials = []
sessionBlockTrials = []
sessionStim = []
sessionRewardStim = []
for obj in exps:
    trials = ~obj.autoRewarded & ~obj.catchTrials
    trialInd = np.where(trials)[0]
    firstTrial = trialInd[0]
    # modality = np.array([stim[:-1]==rew[:-1] for stim,rew in zip(obj.trialStim[trials],obj.rewardedStim[trials])])
    # stimulus = np.array(['1' in stim for stim in obj.trialStim[trials]])
    x['model'].append(obj.trialStim[trials] == obj.rewardedStim[trials])
    x['attention'].append(np.zeros(trials.sum(),dtype=bool))
    x['reinforcement'].append(np.zeros(trials.sum(),dtype=bool))
    x['persistence'].append(np.zeros(trials.sum(),dtype=bool))
    for i,stim in enumerate(obj.trialStim[trials]):
        rewardInd = obj.trialRewarded[:trialInd[i]]
        if rewardInd.sum()>0:
            x['attention'][-1][i] = stim[:-1] in obj.trialStim[np.where(rewardInd)[0][-1]]
        stimInd = obj.trialStim[:trialInd[i]]==stim
        if stimInd.sum()>0:
            x['persistence'][-1][i] = obj.trialResponse[np.where(stimInd)[0][-1]]
            stimRespInd = stimInd & obj.trialResponse[:trialInd[i]]
            if stimRespInd.sum()>0:
                x['reinforcement'][-1][i] = obj.trialRewarded[np.where(stimRespInd)[0][-1]]
    # x['response'].append(np.concatenate(([obj.trialResponse[firstTrial-1]],obj.trialResponse[trials][:-1])))
    # x['reward'].append(np.concatenate(([obj.trialRewarded[firstTrial-1]],obj.trialRewarded[trials][:-1])))
    x['bias'].append(np.ones(trials.sum(),dtype=bool))
    y.append(obj.trialResponse[trials])
    sessionTrials.append(trials.sum())
    sessionBlockTrials.append(np.array([np.sum(obj.trialBlock[trials]==i) for i in np.unique(obj.trialBlock)]))
    sessionStim.append(obj.trialStim[trials]) 
    sessionRewardStim.append(obj.rewardedStim[trials])
sessionStartStop = np.concatenate(([0],np.cumsum(sessionTrials)))
blockTrials = np.concatenate(sessionBlockTrials)

regressorCorr = np.zeros((len(regressors)-1,)*2)
for i,ri in enumerate(regressors[:-1]):
    for j,rj in enumerate(regressors[:-1]):
        regressorCorr[i,j] = np.corrcoef(np.concatenate(x[ri]),np.concatenate(x[rj]))[0,1]



# psytrack
holdOut = ['none']+regressors[:-1]+[('model','attention')]
holdOutColors = 'krbgcm'
hyperparams = {reg: [] for reg in holdOut}
evidence = {reg: [] for reg in holdOut}
modelWeights = {reg: [] for reg in holdOut}
hessian = {reg: [] for reg in holdOut}
cvLikelihood = {reg: [] for reg in holdOut}
cvProbNoLick = {reg: [] for reg in holdOut}
accuracy = {reg: [] for reg in holdOut}
cvFolds = 5
for reg in holdOut:
    for i in range(7,len(exps)):
        print('\n',reg,i)
        d = {'inputs': {key: val[i][:,None].astype(float) for key,val in x.items() if key!=reg and key not in reg},
             'y': y[i].astype(float),
             'dayLength': sessionBlockTrials[i]}
        
        weights = {key: 1 for key in d['inputs']}
        
        nWeights = sum(weights.values())
        
        hyper= {'sigInit': 2**4.,
                'sigma': [2**-4.] * nWeights,
                'sigDay': [2**-4.] * nWeights}
        
        optList = ['sigma','sigDay']
        
        try:
            hyp, evd, wMode, hess_info = psytrack.hyperOpt(d, hyper, weights, optList)
            hyperparams[reg].append(hyp)
            evidence[reg].append(evd)
            modelWeights[reg].append(wMode)
            hessian[reg].append(hess_info)
        except:
            print('\nerror fitting ',reg,i)
            hyperparams[reg].append(None)
            evidence[reg].append(np.nan)
            modelWeights[reg].append(np.full((nWeights,d['y'].size),np.nan))
            hessian[reg].append(None)
        
        if cvFolds is not None:
            cvTrials = d['y'].size - (d['y'].size % cvFolds)
            likelihood = np.nan
            probNoLick = np.full(cvTrials,np.nan)
            if hyperparams[reg][-1] is not None:
                try:
                    likelihood,probNoLick = psytrack.crossValidate(psytrack.trim(d,END=cvTrials), hyper, weights, optList, F=cvFolds, seed=0)
                except:
                    print('\nerror cross validating ',reg, i)
            cvLikelihood[reg].append(likelihood)
            cvProbNoLick[reg].append(probNoLick)
            d['y'] -= 1
            accuracy[reg].append(np.abs(d['y'][:cvTrials] - probNoLick))



preTrials = postTrials = 15
x = np.arange(-preTrials,postTrials+1)
for rewardStim in ('vis1','sound1'):
    visRespProb = []
    soundRespProb = []
    weights = []
    for i in range(len(exps)):
        blockStartStop = np.cumsum(sessionBlockTrials[i])
        lickProb = 1-cvProbNoLick['none'][i]
        mWeights = modelWeights['none'][i]
        for j,(blockStart,blockStop) in enumerate(zip(blockStartStop[:-1],blockStartStop[1:])):
            if sessionRewardStim[i][blockStart]==rewardStim:
                for rp,stim in zip((visRespProb,soundRespProb),('vis1','sound1')):
                    stimTrials = sessionStim[i][:lickProb.size]==stim
                    r = np.full(preTrials+postTrials+1,np.nan)
                    r[:preTrials] = lickProb[:blockStart][stimTrials[:blockStart]][-preTrials:]
                    r[preTrials+1:] = lickProb[blockStart:][stimTrials[blockStart:]][:postTrials]
                    rp.append(r)
                w = np.full((mWeights.shape[0],preTrials+postTrials+1),np.nan)
                for k,mw in enumerate(mWeights):
                    w[k,:preTrials] = mw[blockStart-preTrials:blockStart]
                    w[k,preTrials+1:] = mw[blockStart:blockStart+postTrials]
                weights.append(w)
        
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    ylim = [0,1.01]
    ax.plot([0,0],ylim,'k--')
    for d,clr,lbl in zip((visRespProb,soundRespProb),'gm',('vis','sound')):
        m = np.nanmean(d,axis=0)
        s = np.nanstd(d,axis=0)/(np.sum(~np.isnan(d),axis=0)**0.5)
        ax.plot(x,m,clr,label=lbl)
        ax.fill_between(x,m+s,m-s,color=clr,alpha=0.25)
    for side in ('right','top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out',top=False,right=False)
    ax.set_ylim(ylim)
    ax.set_xlabel('Trial')
    ax.set_ylabel('Response Probability')
    ax.legend(loc='lower right')
    plt.tight_layout()



for i in range(len(exps)):
    w = modelWeights['none'][i]
    wNames = sorted(regressors)
    wColors = [regressorColors[regressors.index(wn)] for wn in wNames]
    fig = plt.figure(figsize=(8,8))
    ax = fig.add_subplot(1,1,1)
    ylim = [min(0,1.05*w.min()),1.05*w.max()]
    for blockEnd in np.cumsum(sessionBlockTrials[i])[:-1]:
        ax.plot([blockEnd+0.5]*2,ylim,'k')
    for w,lbl,clr in zip(w,wNames,wColors):
        ax.plot(np.arange(sessionTrials[i])+1,w,color=clr,label=lbl)
    for side in ('right','top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out',top=False,right=False,labelsize=10)
    ax.set_xlim([0,sessionTrials[i]+1])
    ax.set_ylim(ylim)
    ax.set_xlabel('trial',fontsize=12)
    ax.set_ylabel('weights',fontsize=12)
    ax.legend(bbox_to_anchor=(1,1),fontsize=8)
    ax.set_title(exps[i].subjectName+'_'+exps[i].startTime,fontsize=10)
    plt.tight_layout()


smoothSigma = 5
for i in range(len(exps)):
    lickProbModel= 1-cvProbNoLick['none'][i]
    fig = plt.figure(figsize=(8,8))
    ylim = [-0.05,1.05]
    ax = fig.add_subplot(1,1,1)
    for j,(stim,clr) in enumerate(zip(('vis1','vis2','sound1','sound2'),'rmbc')):
        stimInd = sessionStim[i][:lickProbModel.size] == stim
        blockStart = 0
        smoothedLickProb = []
        smoothedLickProbModel = []
        for blockEnd in np.cumsum(sessionBlockTrials[i]):
            if j==0:
                ax.plot([blockEnd+0.5]*2,ylim,'k')
            blockInd = slice(blockStart,blockEnd)
            trialInd = stimInd[blockInd]
            smoothedLickProb.append(gaussian_filter(y[i].astype(float)[:lickProbModel.size][blockInd][trialInd],smoothSigma))
            smoothedLickProbModel.append(gaussian_filter(lickProbModel[blockInd][trialInd],smoothSigma))
            blockStart = blockEnd
        trials = np.where(stimInd)[0]+1
        ax.plot(trials,np.concatenate(smoothedLickProb),color=clr,label=stim+' (mouse, smoothed)')
        ax.plot(trials,np.concatenate(smoothedLickProbModel),'--',color=clr,label=stim+' (model, smoothed)')
        ax.plot(trials,lickProbModel[stimInd],'o',ms=2,mec=clr,mfc='none',label=stim+' (model)')
    for side in ('right','top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out',top=False,right=False,labelsize=10)
    ax.set_xlim([0,sessionTrials[i]+1])
    ax.set_ylim(ylim)
    ax.set_xlabel('trial',fontsize=12)
    ax.set_ylabel('resp prob',fontsize=12)
    ax.legend(bbox_to_anchor=(1,1.5),fontsize=8)
    ax.set_title(exps[i].subjectName+'_'+exps[i].startTime,fontsize=10)
    plt.tight_layout()


for m,lbl in zip((evidence,cvLikelihood,accuracy),('evidence','likelihood','accuracy')):
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    for reg,clr in zip(holdOut,holdOutColors):
        if lbl=='accuracy':
            a = np.array([np.mean(b) for b in m['none']])
            h = np.array([np.mean(d) for d in m[reg]])
        else:
            a = np.array(m['none'])
            h = np.array(m[reg])
        d = h-a
        dsort = np.sort(d)
        cumProb = np.array([np.sum(d<=i)/d.size for i in dsort])
        ax.plot(dsort,cumProb,color=clr,label=reg)
    for side in ('right','top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out',top=False,right=False,labelsize=10)
    ax.set_ylim([0,1.02])
    ax.set_xlabel('change in model '+lbl,fontsize=12)
    ax.set_ylabel('cumulative prob',fontsize=12)
    ax.legend()
    plt.tight_layout()
    
fig = plt.figure()
ax = fig.add_subplot(1,1,1)
for reg,clr in zip(holdOut,holdOutColors):
    d = np.array([np.mean(a) for a in accuracy[reg]])
    dsort = np.sort(d)
    cumProb = np.array([np.sum(d<=i)/d.size for i in dsort])
    ax.plot(dsort,cumProb,color=clr,label=reg)
for side in ('right','top'):
    ax.spines[side].set_visible(False)
ax.tick_params(direction='out',top=False,right=False,labelsize=10)
ax.set_ylim([0,1.02])
ax.set_xlabel('accuracy',fontsize=12)
ax.set_ylabel('cumulative prob',fontsize=12)
ax.legend()
plt.tight_layout()
    

for ho in holdOut:
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    r,c = zip(*[(r,c) for r,c in zip(regressors,regressorColors) if r!=ho and r not in ho])
    for reg,clr in zip(r,c):
        wNames = sorted(r)
        d = np.array([np.mean(w[wNames.index(reg)]) for w in modelWeights['none']])
        dsort = np.sort(d)
        cumProb = np.array([np.sum(d<=i)/d.size for i in dsort])
        ax.plot(dsort,cumProb,color=clr,label=reg)
    for side in ('right','top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out',top=False,right=False,labelsize=10)
    ax.set_ylim([0,1.02])
    ax.set_xlabel('model weighting',fontsize=12)
    ax.set_ylabel('cumulative prob',fontsize=12)
    ax.set_title(ho)
    ax.legend()
    plt.tight_layout()


# glm-hmm
# hyperparameters
N = y.size # number of data/time points
K = 3 # number of latent states
C = 2 # number of observation classes
D = x.shape[1] # number of GLM inputs (regressors)

# A = transition probabilities
# w = weights
# pi = initial state probabilities

# y = observations (0/1 x n trials)
# x = inputs (n trials x n regressors)
# z = latent states (n trials)

model = glm_hmm.GLMHMM(N,D,C,K,observations="bernoulli",gaussianPrior=1)

inits = 3 # set the number of initializations
maxiter = 250 # maximum number of iterations of EM to allow for each fit
tol = 1e-3

# store values for each initialization
lls_all = np.zeros((inits,250))
A_all = np.zeros((inits,K,K))
w_all = np.zeros((inits,K,D,C))

# fit the model for each initialization
for i in range(inits):
    t0 = time.time()
    # initialize the weights
    A_init,w_init,pi_init = model.generate_params(weights=['GLM',-0.2,1.2,x,y,1])
    # fit the model                     
    lls_all[i,:],A_all[i,:,:],w_all[i,:,:],pi0 = model.fit(y,x,A_init,w_init,maxiter=maxiter,tol=tol,sess=sessionStartStop) 
    minutes = (time.time() - t0)/60
    print('initialization %s complete in %.2f minutes' %(i+1, minutes))


















