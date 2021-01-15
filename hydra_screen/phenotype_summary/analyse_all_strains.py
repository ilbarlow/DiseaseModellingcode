#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 09:15:35 2020

@author: ibarlow

Script that loops through all the strains and does first step of
k sig features, bluelight features and ts plots
"""

import pandas as pd
# import numpy as np
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from tierpsytools.analysis.significant_features import k_significant_feat
from tierpsytools.preprocessing.preprocess_features import impute_nan_inf
from tierpsytools.read_data.hydra_metadata import align_bluelight_conditions
import time

sys.path.insert(0, '/Users/ibarlow/Documents/GitHub/pythonScripts/DiseaseModelling/hydra_screen/phenotype_summary')
from helper import (read_disease_data,
                    select_strains,
                    filter_features,
                    make_colormaps,
                    find_window,
                    strain_gene_dict,
                    long_featmap,
                    BLUELIGHT_WINDOW_DICT,
                    DATES_TO_DROP)
from plotting_helper import  (plot_colormap,
                              make_clustermaps,
                              clustered_barcodes,
                              feature_box_plots,
                              window_errorbar_plots,
                              CUSTOM_STYLE)
from ts_helper import (align_bluelight_meta,
                       load_bluelight_timeseries_from_results,
                       make_feats_abs,
                       plot_strains_ts,
                       get_motion_modes,
                        # get_frac_motion_modes_with_ci,
                       plot_frac)

ANALYSIS_TYPE = ['timeseries']# , 'timeseries']#, 'bluelight', ]
motion_modes=True
exploratory = False
do_stats=False
is_reload_timeseries_from_results = False
is_recalculate_frac_motion_modes = False

ROOT_DIR = Path('/Users/ibarlow/OneDrive - Imperial College London/Documents/behavgenom_copy/DiseaseScreen')
FEAT_FILE = list(ROOT_DIR.rglob('*filtered/features_summary_tierpsy_plate_20200930_125752.csv'))[0] #Path('/Users/ibarlow/OneDrive - Imperial College London/Documents/behavgenom_copy/DiseaseScreen/summary_results_files/filtered/features_summary_tierpsy_plate_20200930_125752.csv')
FNAME_FILE = list(ROOT_DIR.rglob('*filtered/filenames_summary_tierpsy_plate_20200930_125752.csv'))[0] #Path('/Users/ibarlow/OneDrive - Imperial College London/Documents/behavgenom_copy/DiseaseScreen/summary_results_files/filtered/filenames_summary_tierpsy_plate_20200930_125752.csv')
METADATA_FILE = list(ROOT_DIR.rglob('*wells_annotated_metadata.csv'))[0] #Path('/Users/ibarlow/OneDrive - Imperial College London/Documents/behavgenom_copy/DiseaseScreen/AuxiliaryFiles/wells_annotated_metadata.csv')

RAW_DATA_DIR = Path('/Volumes/Ashur Pro2/DiseaseScreen')
WINDOW_FILES = RAW_DATA_DIR / 'Results' / 'window_summaries'

CONTROL_STRAIN = 'N2'
BAD_FEAT_THRESH = 3 # 3 standard deviations away from the mean
BAD_FEAT_FILTER = 0.1 # 10% threshold for removing bad features
BAD_WELL_FILTER = 0.3 # 30% threshold for bad well

strains_done = []#['add-1', 'bbs-2', 'C43B7.2', 'cat-2', 'glc-2', 'glr-1', 'gpb-2', 'mpx-1', 'nca-2','pink-1', 'snf-11', 'unc-43',  'unc-49', 'unc-77', ] #['mpz-1', 'snf-11', 'C43B7.2', 'unc-43'] add in myo and unc-54 here (.isin() method)

feat256_fname = Path('/Users/ibarlow/tierpsy-tools-python/tierpsytools/extras/feat_sets/tierpsy_256.csv')

#%%
if __name__ == '__main__':

    #set style for all figures
    plt.style.use(CUSTOM_STYLE)
    sns.set_style('ticks')

    feat, meta = read_disease_data(FEAT_FILE,
                                   FNAME_FILE,
                                   METADATA_FILE,
                                   export_nan_worms=False)

    window_files = list(WINDOW_FILES.rglob('*_window_*'))
    window_feat_files = [f for f in window_files if 'features' in str(f)]
    window_feat_files.sort(key=find_window)
    window_fname_files = [f for f in window_files if 'filenames' in str(f)]
    window_fname_files.sort(key=find_window)

    assert (find_window(f[0]) == find_window(f[1]) for f in list(zip(window_feat_files, window_fname_files)))

    genes = [g for g in meta.worm_gene.unique() if g != CONTROL_STRAIN]
    genes = [g for g in genes if 'myo' not in g and 'unc-54' not in g]

    genes = list(set(genes) - set(strains_done))

    for count, g in enumerate(genes):
        #TODO add in the counting timer
        print('Analysing {} {}/{}'.format(g, count+1, len(genes)))
        candidate_gene = g

        saveto = ROOT_DIR / 'Figures' / 'paper_figures' / candidate_gene
        saveto.mkdir(exist_ok=True)

        if 'all_stim' in ANALYSIS_TYPE:

            print ('all stim plots for {}'.format(candidate_gene))


            feat_df, meta_df, idx, gene_list = select_strains(candidate_gene,
                                                              CONTROL_STRAIN,
                                                              feat_df=feat,
                                                              meta_df=meta)
            # filter features
            feat_df, meta_df, featsets = filter_features(feat_df,
                                                         meta_df)

            strain_lut, stim_lut, feat_lut = make_colormaps(gene_list,
                                                            idx,
                                                            candidate_gene,
                                                            CONTROL_STRAIN,
                                                            featlist=featsets['all'])

            # colorbars to map colors to strains
            plot_colormap(strain_lut)
            plt.savefig(saveto / 'strain_cmap.png')
            plt.close('all')
            ax = plot_colormap(stim_lut)
            plt.savefig(saveto / 'stim_cmap.png')
            #%%  fillnans and normalise by bluelight condition
            # long_feat, long_meta = long_featmap(feat_df,
            #                                     meta_df)
            # feat_nonan = pd.concat([long_feat,
            #                         long_meta],
            #                        axis=1).groupby('bluelight').apply(impute_nan_inf)[long_feat.columns]
            # feat_nonan.reset_index(level='bluelight',
            #                        drop=False,
            #                        inplace=True)
            # feat_nonan.sort_index(inplace=True)
            # long_meta.sort_index(inplace=True)

            feat_nonan = impute_nan_inf(feat_df)

            # feat_nonan, meta_nonan = align_bluelight_conditions(feat_nonan, long_meta[pd.read_csv(METADATA_FILE).columns])

            featZ = pd.DataFrame(data=stats.zscore(feat_nonan[featsets['all']], axis=0),
                                 columns=featsets['all'],
                                 index=feat_nonan.index)

            assert featZ.isna().sum().sum() == 0
            #%% make a nice clustermap / heatmap
            (saveto / 'clustermaps').mkdir(exist_ok=True)

            #TODO should I use one of sklearns algorithms instead?
            clustered_features = make_clustermaps(featZ,
                                                  meta,
                                                  featsets,
                                                  strain_lut,
                                                  feat_lut,
                                                  saveto=saveto / 'clustermaps')
            plt.close('all')

            #%% k significant features for each prestim, bluelight and poststim
            if exploratory:
                (saveto / 'ksig_feats').mkdir(exist_ok=True)
                sns.set_style('white')
                label_format = '{:.4f}'
                kfeats = {}
                for stim, fset in featsets.items():
                    kfeats[stim], scores, support = k_significant_feat(
                        feat_nonan[fset],
                        meta_df.worm_gene,
                        k=100,
                        plot=False)

                    for i in range(0,5):
                        fig, ax = plt.subplots(4, 5, sharex=True, figsize = [20,20])
                        for c, axis in enumerate(ax.flatten()):
                            counter=(20*i)-(20-c)
                            sns.boxplot(x=meta_df['worm_gene'],
                                        y=feat_df[kfeats[stim][counter]],
                                        palette=strain_lut.values(),
                                        ax=axis)
                            axis.set_ylabel(fontsize=8,
                                            ylabel=kfeats[stim][counter])
                            axis.set_yticklabels(labels=[label_format.format(x) for x in axis.get_yticks()],
                                                 fontsize=6)
                            axis.set_xlabel('')
                        plt.tight_layout()
                        fig.fontsize=11
                        plt.savefig(saveto / 'ksig_feats' / '{}_{}_ksig_feats.png'.format(i*20, stim),
                                    dpi=400)
                        plt.close('all')

            # pairwise statistics to find features that are different from N2
            else:
                (saveto / 'heatmaps').mkdir(exist_ok=True)
                (saveto / 'boxplots').mkdir(exist_ok=True)

                if do_stats:
                    from tierpsytools.analysis.pairwise_stats_tests import pairwise_stats_tests
                    pVals, bhP_values, group_classes = pairwise_stats_tests(features=feat_df,
                                                                           y_classes=meta_df.loc[:, 'worm_gene'],
                                                                           control_group=CONTROL_STRAIN)
                    bhP_values['worm_gene'] = group_classes
                    bhP_values.rename(mapper={0:'p<0.05'},
                                      inplace=True)

                    with open(saveto / 'sig_feats.txt', 'w+') as fid:
                        fid.write(str(bhP_values.notna().sum().sum()-1) + ' significant features out of \n')
                        fid.write(str(bhP_values.shape[1]))

                    bhP_values.to_csv(saveto / '{}_stats.csv'.format(candidate_gene),
                                      index=False)
                # bhP_values.set_index('worm_gene', inplace=True)
                else:
                    bhP_values = pd.read_csv(saveto / '{}_stats.csv'.format(candidate_gene),
                                             index_col=False)
                #%%

                #import the selected features
                feat_to_plot_fname = list(saveto.rglob('feats_to_plot.txt'))[0]
                selected_feats = []
                with open(feat_to_plot_fname, 'r') as fid:
                    for l in fid.readlines():
                        selected_feats.append(l.rstrip().strip(','))

                all_stim_selected_feats=[]
                for s in selected_feats:
                    all_stim_selected_feats.extend([f for f in featsets['all'] if '_'.join(s.split('_')[:-1])=='_'.join(f.split('_')[:-1])])

                # nice figure with single barcode for each strains, and asterisks of signficicantly different features

                clustered_barcodes(clustered_features, selected_feats,
                                   featZ,
                                   meta,
                                   bhP_values,
                                   saveto / 'heatmaps')

                # and make nice plots of the selected figures
                for f in  all_stim_selected_feats:
                    feature_box_plots(f,
                                      feat_df,
                                      meta_df,
                                      strain_lut,
                                       bhP_values
                                      )
                    plt.savefig(saveto / 'boxplots' / '{}_boxplot.png'.format(f),
                                dpi=200)
                plt.close('all')

        # %% bluelight
        if 'bluelight' in ANALYSIS_TYPE:
            print ('all window_plots for {}'.format(candidate_gene))

            feat_windows = []
            meta_windows = []
            for c,f in enumerate(list(zip(window_feat_files, window_fname_files))):
                _feat, _meta = read_disease_data(f[0],
                                                 f[1],
                                                 METADATA_FILE,
                                                 drop_nans=True)
                _meta['window'] = find_window(f[0])
                # feat_df, meta_df = drop_nan_worms(feat_df, meta_df, saveto=None)
                _feat, _meta, idx, gene_list = select_strains(candidate_gene,
                                                              CONTROL_STRAIN,
                                                              _meta,
                                                              _feat)
                meta_windows.append(_meta)
                feat_windows.append(_feat)

            meta_windows = pd.concat(meta_windows)
            meta_windows.reset_index(drop=True,
                                     inplace=True)
            feat_windows = pd.concat(feat_windows)
            feat_windows.reset_index(drop=True,
                                     inplace=True)

            #only need the bluelight features
            bluelight_feats = [f for f in feat_windows.columns if 'bluelight' in f]
            feat_windows = feat_windows[bluelight_feats]

            feat_windows, meta_windows, featsets = filter_features(feat_windows,
                                                                   meta_windows)

            bluelight_feats = [f for f in feat_windows.columns if 'bluelight' in f]
            strain_lut, stim_lut, feat_lut = make_colormaps(gene_list,
                                                            idx,
                                                            candidate_gene,
                                                            CONTROL_STRAIN,
                                                            featlist=bluelight_feats)

            #%% fillnans and normalize
            feat_nonan = impute_nan_inf(feat_windows)

            featZ = pd.DataFrame(data=stats.zscore(feat_nonan[bluelight_feats], axis=0),
                                 columns=bluelight_feats,
                                 index=feat_nonan.index)

            assert featZ.isna().sum().sum() == 0

            #%%
            # find the k sig feats that differentiate between prelight and bluelight

            (saveto / 'windows_features').mkdir(exist_ok=True)
            meta_windows['light'] = [x[1] for x in meta_windows['window'].map(BLUELIGHT_WINDOW_DICT)]
            meta_windows['window_sec'] = [x[0] for x in meta_windows['window'].map(BLUELIGHT_WINDOW_DICT)]


            y_classes = ['{}, {}'.format(r.worm_gene, r.light) for i,r in meta_windows.iterrows()]

            kfeats, scores, support = k_significant_feat(
                    feat_nonan,
                    y_classes,
                    k=100,
                    plot=False,
                    score_func='f_classif')

            for f in kfeats[:50]:
                window_errorbar_plots(f,
                                      feat_windows,
                                      meta_windows,
                                      strain_lut)
                plt.savefig(saveto / 'windows_features' / '{}'.format(f), dpi=200)
                plt.close('all')
            #%% motion modes
            if motion_modes:
                mm_feats = [f for f in bluelight_feats if 'motion_mode' in f]
                (saveto / 'windows_features' / 'motion_modes').mkdir(exist_ok=True)
                for f in mm_feats:
                    window_errorbar_plots(f,
                                          feat_windows,
                                          meta_windows,
                                          strain_lut)
                    plt.savefig(saveto / 'windows_features' / 'motion_modes' / '{}'.format(f),
                                dpi=200)
                    plt.close('all')
        #%% make nice ts plots

        if 'timeseries' in ANALYSIS_TYPE:
            print ('timeseries plots for {}'.format(candidate_gene))

            timeseries_fname = RAW_DATA_DIR / 'Results' / '{}_timeseries.hdf5'.format(candidate_gene)

            meta_ts = pd.read_csv(METADATA_FILE, index_col=None)
            assert meta_ts.worm_strain.unique().shape[0] == meta_ts.worm_gene.unique().shape[0]

            meta_ts.loc[:,'date_yyyymmdd'] = meta_ts['date_yyyymmdd'].apply(lambda x: str(int(x)))
            #drop nan wells
            meta_ts.dropna(axis=0,
                        subset=['worm_gene'],
                        inplace=True)
            # remove data from dates to exclude
            good_date = meta_ts.query('@DATES_TO_DROP not in imaging_date_yyyymmdd').index
            # bad wells
            good_wells_from_gui = meta_ts.query('is_bad_well == False').index
            meta_ts = meta_ts.loc[good_wells_from_gui & good_date,:]

            # only select strains of interest
            meta_ts, idx, gene_list = select_strains(candidate_gene,
                                                  CONTROL_STRAIN,
                                                  meta_df=meta_ts)
            strain_lut, stim_lut = make_colormaps(gene_list,
                                                    idx,
                                                    candidate_gene,
                                                    CONTROL_STRAIN,
                                                    featlist=[])
            #strain to gene dictionary
            strain_dict = strain_gene_dict(meta_ts)
            gene_dict = {v:k for k,v in strain_dict.items()}

            meta_ts = align_bluelight_meta(meta_ts)

            if is_reload_timeseries_from_results:
                # this uses tierpytools under the hood
                timeseries_df, hires_df  = load_bluelight_timeseries_from_results(
                                    meta_ts,
                                    RAW_DATA_DIR / 'Results')
                                    # save to disk
                try:
                    timeseries_df.to_hdf(timeseries_fname, 'timeseries_df', format='table')
                    hires_df.to_hdf(timeseries_fname, 'hires_df', format='table')
                except Exception:
                    print ('error creating {} HDF5 file'.format(candidate_gene))
            else:  # from disk, then add columns
                # dataframe from the saved file
                timeseries_df = pd.read_hdf(timeseries_fname, 'timeseries_df')
                hires_df = pd.read_hdf(timeseries_fname, 'hires_df')

            #%% add in information about the replicates
            date_to_repl = pd.DataFrame({'date_yyyymmdd': [
                                                          '20200730',
                                                         '20200801',
                                                         '20200806',
                                                         '20200808',
                                                         '20200811',
                                                         '20200813',
                                                        '20200902',
                                                        '20200903',
                                                        '20200904'
                                                           ],
                                     'replicate': [1, 1, 2, 2, 3, 3, 1, 2, 3]})
            timeseries_df = pd.merge(timeseries_df, date_to_repl,
                                     how='left',
                                     on='date_yyyymmdd')

            timeseries_df['worm_strain'] = timeseries_df['worm_gene'].map(gene_dict)
            hires_df['worm_strain'] = hires_df['worm_gene'].map(gene_dict)

            #make d/v signed features absolute as in hydra d/v is not assigned
            timeseries_df = make_feats_abs(timeseries_df)


            # %%% hand-picked features from the downsampled dataframe

            plt.close('all')
            (saveto / 'ts_plots').mkdir(exist_ok=True)
            feats_toplot = ['speed',
                            'abs_speed',
                            'angular_velocity',
                            'abs_angular_velocity',
                            'relative_to_body_speed_midbody',
                            'abs_relative_to_body_speed_midbody',
                            'abs_relative_to_neck_angular_velocity_head_tip',
                            'speed_tail_base',
                            'length',
                            'major_axis',
                            'd_speed',
                            'head_tail_distance',
                            'abs_angular_velocity_neck',
                            'abs_angular_velocity_head_base',
                            'abs_angular_velocity_hips',
                            'abs_angular_velocity_tail_base',
                            'abs_angular_velocity_midbody',
                            'abs_angular_velocity_head_tip',
                            'abs_angular_velocity_tail_tip']

            plot_strains_ts(timeseries_df,
                            strain_lut,
                            CONTROL_STRAIN,
                            feats_toplot,
                            saveto / 'ts_plots')
            plt.close('all')
            #%% motion modes
            # get motion_mode stats
            tic = time.time()
            if is_recalculate_frac_motion_modes:
                motion_modes, frac_motion_modes_with_ci = get_motion_modes(hires_df,
                                                                            saveto=timeseries_fname
                                                                           )
            else:
                frac_motion_modes_with_ci = pd.read_hdf(timeseries_fname,
                                                       'frac_motion_mode_with_ci')

            frac_motion_modes_with_ci['worm_strain'] = frac_motion_modes_with_ci['worm_gene'].map(gene_dict)

            fps = 25
            frac_motion_modes_with_ci = frac_motion_modes_with_ci.reset_index()
            frac_motion_modes_with_ci['time_s'] = (frac_motion_modes_with_ci['timestamp']
                                                  / fps)
            print('Time elapsed: {}s'.format(time.time()-tic))

            # %% make some nicer plotes with confindence intervals using luigi's bootstrapping
            for ii, (strain, df_g) in enumerate(frac_motion_modes_with_ci.groupby('worm_gene')):
                plot_frac(df_g, strain, strain_lut)
                plt.savefig(saveto / '{}_motion_modes.png'.format(strain), dpi=200)
