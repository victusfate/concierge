import os
import json
import sh
import sys
import tempfile
import zipfile
import math

import numpy as np
import pandas as pd

from . import constants
from .constants import s3
from rsyslog_cee import log
config = constants.CONFIG

ENV = constants.ENVIRONMENT
AWS_BUCKET = constants.AWS_BUCKET

RATINGS_FILE = constants.RATINGS_FILE

ITEM_COLUMN = constants.ITEM_COLUMN
RATING_COLUMN = constants.RATING_COLUMN
CITY_COLUMN = constants.CITY_COLUMN
HOOD_COLUMN = constants.HOOD_COLUMN
USER_COLUMN = constants.USER_COLUMN
TIMESTAMP_COLUMN = constants.TIMESTAMP_COLUMN
HOUR_COLUMN = constants.HOUR_COLUMN
DAY_COLUMN = constants.DAY_COLUMN

RATING_COLUMNS = constants.RATING_COLUMNS

MAX_RATING = constants.MAX_RATING

def read_dataset(delimiter, input_file): 
  """Load dataset, and create train and set sparse matrices.

  Assumes USER_COLUMN, ITEM_COLUMN, RATING_COLUMN, and CITY_COLUMN columns.

  Args:
    delimiter: file delimiter
    input_file: path to csv data file

  Returns:
    loaded csv
  """
  # scores_df = pd.read_csv(input_file, sep=',', header=0)
  use_headers = None

  headers = [USER_COLUMN, ITEM_COLUMN, RATING_COLUMN, TIMESTAMP_COLUMN]
  header_row = 0 if use_headers else None  
  # todo filter any nans or rows with missing properties from the dataset
  df = pd.read_csv(input_file,
                           sep=delimiter,
                           names=headers,
                           header=header_row,
                           dtype={
                               USER_COLUMN: str,
                               ITEM_COLUMN: str,
                               RATING_COLUMN: np.float32,
                               TIMESTAMP_COLUMN: int
                           },
                           encoding="utf-8")
  # print('read_dataset missing values',df.isnull().sum())
  # df.dropna(inplace=True)
  # print('read_dataset after removing missing values',df.isnull().sum())
  return df


def load_dataset(delimiter, input_file): 
  """Load dataset, and create train and set sparse matrices.

  Assumes 'user_id', 'item_id', 'rating', and 'city_id' columns.

  Args:
    delimiter: file delimiter
    input_file: path to csv data file

  Returns:
    array of user IDs for each row of the ratings matrix
    array of item IDs for each column of the rating matrix
    sparse coo_matrix for training
    sparse coo_matrix for test
  """
  # scores_df = pd.read_csv(input_file, sep=',', header=0)
  df_user_item_scores = read_dataset(delimiter,input_file)

  # if we only wanted positive ratings
  # cols = [constants.RATING_COLUMN]
  # df_user_item_scores = df_user_item_scores[df_user_item_scores[cols] > 0]
  grouped = df_user_item_scores.groupby(constants.USER_COLUMN)
  df_user_item_scores = grouped.filter(
      lambda x: len(x) >= constants.MIN_NUM_RATINGS) # type: pd.DataFrame
  return df_user_item_scores



