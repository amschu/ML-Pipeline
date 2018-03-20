"""
PURPOSE:
Run feature selection method available from sci-kit learn on a given dataframe

Must set path to Miniconda in HPC:  export PATH=/mnt/home/azodichr/miniconda3/bin:$PATH


INPUT:
  -df       Feature dataframe for ML. Format -> Col 1 = example.name, Col 2 = Class, Col 3-... = Features.
  -f        Feature selection method to use 
                - Chi2
                - RandomForest
                - Enrichment with Fisher's Exact Test (binary feat only) (default pval = 0.05)
                - LASSO (need -p, -type))
                - Relief (https://github.com/EpistasisLab/scikit-rebate)

OPTIONAL INPUT:
  -feat     Default: all (i.e. everything in the dataframe given). Can import txt file with list of features to keep.
  -class    Name of class column (Default = 'Class')
  -pos      String for what codes for the positive example (i.e. UUN) Default = 1
  -neg      String for what codes for the negative example (i.e. NNN) Default = 0
  -type     r = regression, c = classification
  -p        Parameter value for LASSO (L1) or Fisher's Exact Test.
            Fishers: pvalue cut off (Default = 0.05)
            LASSO: If type = r: need alpha value, try 0.01, 0.001. (larger = fewer features selected)
            LASSO: If type = c: need C which controls the sparcity, try 0.01, 0.1 (smaller = fewer features selected)
  -n        Number of features you would like to keep for RF or chi2
  -list     T/F Save a list of the selected features (useful for ML_classification.py -feat) (Default: F)

OUTPUT:
  -df_f.txt    New dataframe with columns only from feature selection


AUTHOR: Christina Azodi

REVISIONS:   Submitted 8/16/2016

"""
import pandas as pd
import numpy as np
import sys, os


def SaveTopFeats(top, save_name):

    try:
      top.remove('Class')
    except:
      pass

    out = open(save_name, 'w')
    for f in top:
      out.write(f + '\n')




def DecisionTree(df, n, TYPE, save_name):
  """Feature selection using DecisionTree on the whole dataframe
  Feature importance from the Random Forest Classifier is the Gini importance
  (i.e. the normalized total reduction of the criterion for the decendent nodes
    compared to the parent node brought by that feature across all trees.)
  """
  from sklearn.ensemble import RandomForestClassifier
  from sklearn.ensemble import RandomForestRegressor
  from math import sqrt

  X_all = df.drop('Class', axis=1).values  
  Y_all = df.loc[:, 'Class'].values

  fean_num_feat_sel = len(list(df.columns.values)[1:])
  if TYPE.lower() == 'c':
    feat_sel_forest = RandomForestClassifier(criterion='entropy', max_features= round(sqrt(fean_num_feat_sel)), n_estimators=500, n_jobs=1)
  elif TYPE.lower() == 'r':
    Y_all = Y_all.astype('float')
    feat_sel_forest = RandomForestRegressor(max_features= round(sqrt(fean_num_feat_sel)), n_estimators=500, n_jobs=1)
  else:
    print('Need to specify -type r/c (regression/classification)')
    exit()

  print("=====* Running decision tree based feature selection *=====")

  #Train the model & derive importance scores
  feat_sel_forest = feat_sel_forest.fit(X_all, Y_all)
  importances = feat_sel_forest.feature_importances_

  # Sort importance scores and keep top n
  feat_names = list(df.columns.values)[1:]
  temp_imp = pd.DataFrame(importances, columns = ["imp"], index=feat_names) 
  indices = np.argsort(importances)[::-1]

  for n_size in n:
    indices_keep = indices[0:int(n_size)]
    fixed_index = []
    # Translate keep indices into the indices in the df
    for i in indices_keep:
      new_i = i + 1
      fixed_index.append(new_i)
    fixed_index = [0] + fixed_index
    good = [df.columns[i] for i in fixed_index]
    print("Features selected using DecisionTree feature selection: %s" % str(good))

    save_name2 = save_name + "_" + str(n_size)
    SaveTopFeats(good, save_name2)

  
  
def Chi2(df, n, save_name):
  """Feature selection using Chi2 on the whole dataframe. 
  Chi2 measures the dependence between stochastic variables, this method 
  weeds out features that are most likely to be independent of class"""
  from sklearn.feature_selection import SelectKBest
  from sklearn.feature_selection import chi2
  from sklearn.feature_selection import mutual_info_classif 

  print('This function might not be working right now.... Bug Christina if you need it!')
  X_all = df.drop('Class', axis=1).values  
  Y_all = df.loc[:, 'Class'].values
  Y_all = Y_all.astype('int')
  print(Y_all)
  # Set selection to chi2 with n to keep
  for n_size in n:
    # Set selection to chi2 with n to keep
    ch2 = SelectKBest(chi2, k=n)
    ch2.fit_transform(X_all, Y_all)
    index = ch2.get_support(indices=True)

    # Translate keep indices into the indices in the df
    fixed_index = []
    for i in index:
      new_i = i + 1
      fixed_index.append(new_i)
    fixed_index = [0] + fixed_index

    good = [df.columns[i] for i in fixed_index]
    print("Features selected using DecisionTree feature selection: %s" % str(good))

    save_name2 = save_name + "_" + str(n_size)
    SaveTopFeats(good, save_name2)


def Relief(df, n, n_jobs, save_name):
  """Feature selection using Relief on the whole dataframe."""
  from skrebate import ReliefF

  X_all = df.drop('Class', axis=1).values  
  Y_all = df.loc[:, 'Class'].values
  Y_all = Y_all.astype('int')

  feature_names = list(df)
  feature_names.remove('Class')
  print("=====* Running relief/rebase based feature selection *=====")

  # Set selection to relief
  fs = ReliefF(n_jobs = int(n_jobs))
  fs.fit(X_all, Y_all)
  imp = pd.DataFrame(fs.feature_importances_, index = feature_names, columns = ['relief_imp'])
  imp_top = imp.sort_values(by='relief_imp', ascending=False)

  for n_size in n:
    keep = imp_top.index.values[0:int(n_size)]
    print("Features selected using Relief from rebase: %s" % str(keep))
    save_name2 = save_name + "_" + str(n_size)
    SaveTopFeats(keep, save_name2)



def L1(df, PARAMETER, TYPE, save_name):
  """Apply a linear model with a L1 penalty and select features who's coefficients aren't 
  shrunk to zero. Unlike Chi2, this method accounts for the effect of all of the
  other features when determining if a feature is a good predictor.
  For a regression problem, it uses linear_model.Lasso
  For a classification problem, it uses svm.LinearSVC """

  from sklearn.feature_selection import SelectFromModel
  from sklearn.svm import LinearSVC
  from sklearn.linear_model import Lasso

  X_all = df.drop('Class', axis=1).values  
  Y_all = df.loc[:, 'Class'].values
  Y_all = Y_all.astype('int')

  if TYPE == 'c' or TYPE == 'classification':
    estimator = LinearSVC(C = PARAMETER, penalty='l1', dual=False).fit(X_all, Y_all)
  elif TYPE == 'r' or TYPE == 'regression':
    estimator = Lasso(alpha = PARAMETER).fit(X_all, Y_all)

  print("=====* Running L1/LASSO based feature selection *=====")
  
  model = SelectFromModel(estimator, prefit=True)
  keep = model.get_support([])

  X_new = model.transform(X_all)
  feat_names = np.array(list(df)[1:])
  good = feat_names[keep]
  
  print("Features selected using l2: %s" % str(good))
  print('Number of features selected using l2 (parameter = %s): %i' % (str(PARAMETER), X_new.shape[1]))
  
  save_name2 = save_name 
  SaveTopFeats(good, save_name2)

def FET(df, PARAMETER, pos, neg, save_name):
  """Use Fisher's Exact Test to look for enriched features"""
  from scipy.stats import fisher_exact

  kmers = list(df)
  kmers.remove(CL)

  enriched = [CL]
  
  print("=====* Running enrichement based feature selection *=====")
  
  for k in kmers:
    temp = df.groupby([CL, k]).size().reset_index(name="Count")
    try:
      TP = temp.loc[(temp[CL] == pos) & (temp[k] == 1), 'Count'].iloc[0]
    except:
      TP = 0
    try:
      TN = temp.loc[(temp[CL] == neg) & (temp[k] == 0), 'Count'].iloc[0]
    except:
      TN = 0
    try:
      FP = temp.loc[(temp[CL] == neg) & (temp[k] == 1), 'Count'].iloc[0]
    except:
      FP = 0
    try:
      FN = temp.loc[(temp[CL] == pos) & (temp[k] == 0), 'Count'].iloc[0]
    except:
      FN = 0

    oddsratio,pvalue = fisher_exact([[TP,FN],[FP,TN]],alternative='greater')
      
    if pvalue <= PARAMETER:
      enriched.append(k)

  save_name2 = save_name 
  SaveTopFeats(enriched, save_name2)

if __name__ == "__main__":
  
  #Default parameters
  FEAT = 'all'    #Features to include from dataframe. Default = all (i.e. don't remove any from the given dataframe)
  neg = 0    #Default value for negative class = 0
  pos = 1    #Default value for positive class = 1
  save_list = 'false'
  p = 0.05
  CL = 'Class'
  TYPE = 'c'
  n_jobs = 1
  IGNORE, CVs, REPS = 'pass', 'pass', 1
  SEP = '\t'
  SAVE, DF_CLASS = 'default', 'default'
  UNKNOWN = 'unk'
  class_col = 'Class'

  for i in range (1,len(sys.argv),2):

        if sys.argv[i] == "-df":
          DF = sys.argv[i+1]
        if sys.argv[i] == "-df_class":
          DF_CLASS = sys.argv[i+1]
        if sys.argv[i] == "-sep":
          SEP = sys.argv[i+1]
        if sys.argv[i] == '-save':
          SAVE = sys.argv[i+1]
        if sys.argv[i] == '-list':
          save_list = sys.argv[i+1]
        if sys.argv[i] == '-f':
          F = sys.argv[i+1]
        if sys.argv[i] == '-n':
          N = sys.argv[i+1]
        if sys.argv[i] == '-n_jobs':
          n_jobs = int(sys.argv[i+1])
        if sys.argv[i] == '-feat':
          FEAT = sys.argv[i+1]
        if sys.argv[i] == '-p':
          PARAMETER = float(sys.argv[i+1])        
        if sys.argv[i] == '-type':
          TYPE = sys.argv[i+1]
        if sys.argv[i] == '-class':
          CL = sys.argv[i+1]
        if sys.argv[i] == '-pos':
          pos = sys.argv[i+1]
        if sys.argv[i] == '-neg':
          neg = sys.argv[i+1]
        if sys.argv[i] == '-ignore':
          IGNORE = sys.argv[i+1]
        if sys.argv[i] == '-CVs':
          CVs = sys.argv[i+1]
        if sys.argv[i] == '-jobNum':
          jobNum = sys.argv[i+1]


  if len(sys.argv) <= 1:
    print(__doc__)
    exit()

  #Load feature matrix and save feature names 
  df = pd.read_csv(DF, sep=SEP, index_col = 0)


  # If feature info and class info are in separate files
  if DF_CLASS != 'default':
    start_dim = df.shape
    df_class_file, df_class_col = DF_CLASS.strip().split(',')
    class_col = df_class_col
    df_class = pd.read_csv(df_class_file, sep=SEP, index_col = 0)
    df = pd.concat([df_class[df_class_col], df], axis=1, join='inner')
    print('Merging the feature & class dataframes changed the dimensions from %s to %s (instance, features).' 
      % (str(start_dim), str(df.shape)))

  print('Original dataframe contained %i features' % df.shape[1])
  
  if class_col != 'Class':
    df = df.rename(columns = {class_col:'Class'})
  #Recode class as 1 for positive and 0 for negative
  if TYPE.lower() == 'c':
    df["Class"] = df["Class"].replace(pos, 1)
    df["Class"] = df["Class"].replace(neg, 0)

  df = df.dropna(axis=0, how = 'any')

  # If requesting multiple n, convert to list
  try:
    N = N.strip().split(',')
  except:
    N = [N]
  print(N)

  #If 'features to keep' list given, remove columns not in that list
  if FEAT != 'all':
    with open(FEAT) as f:
      features = f.read().splitlines()
      features = ['Class'] + features
    df = df.loc[:,features]
  print(df.head())
  

  # Run feature selection
  df_use = df.copy()
  
  # Run FS within a cross-validation scheme
  if CVs != 'pass':
    print("Working on cv_%s" % str(jobNum))
    cv_folds = pd.read_csv(CVs, sep=',', index_col=0)
    cv = cv_folds['cv_' + str(jobNum)]
    df_use['Class'][cv==5] = 'unk'


  # Remove any unknown class values from the data frame
  if UNKNOWN in df_use.loc[:, 'Class'].values:
    df_use = df_use[df_use.Class != UNKNOWN]

  if SAVE != 'default':
    save_name = SAVE
  else:
    try:
      save_name = DF.split("/")[-1] + "_" + F + '_cv' + str(jobNum)
    except:
      save_name = DF.split("/")[-1] + "_" + F

  if F.lower() == "randomforest" or F.lower() == "rf":
    DecisionTree(df_use, N, TYPE, save_name)
    
  elif F.lower() == "chi2" or F.lower() == "c2":
    Chi2(df_use, N, save_name)
    
  elif F.lower() == "l1" or F.lower() == "lasso":
    if SAVE == 'default':
      save_name = save_name + '_' + str(PARAMETER)
    L1(df_use, PARAMETER, TYPE, save_name)
    
  elif F.lower() == "relief" or F.lower() == "rebate":
    Relief(df_use, N, n_jobs, save_name)
    
  elif F.lower() == "fisher" or F.lower() == "fet" or F.lower() == 'enrich':
    if SAVE == 'default':
      save_name = save_name + '_' + str(PARAMETER)
    FET(df_use, PARAMETER, pos, neg, save_name)
  


