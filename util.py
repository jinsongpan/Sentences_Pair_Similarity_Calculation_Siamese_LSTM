# -*- coding: utf-8 -*-
# @Author  : Junru_Lu
# @File    : util.py
# @Software: PyCharm
# @Environment : Python 3.6+
# @Reference : https://github.com/likejazz/Siamese-LSTM

# 基础包
from keras import backend as K
from keras.layers import Layer
from keras.preprocessing.sequence import pad_sequences
from gensim.models import KeyedVectors
from scipy.spatial.distance import pdist
import numpy as np
import itertools

'''
本配置文件提供了一系列预定义函数
'''


# ------------------自定义函数------------------ #

def text_to_word_list(text):  # 文本分词
    text = str(text)
    text = text.lower()

    '''
    # 英文文本下的文本清理规则
    import re
    text = re.sub(r"[^A-Za-z0-9^,!.\/'+-=]", " ", text)
    text = re.sub(r"what's", "what is ", text)
    text = re.sub(r"\'s", " ", text)
    text = re.sub(r"\'ve", " have ", text)
    text = re.sub(r"can't", "cannot ", text)
    text = re.sub(r"n't", " not ", text)
    text = re.sub(r"i'm", "i am ", text)
    text = re.sub(r"\'re", " are ", text)
    text = re.sub(r"\'d", " would ", text)
    text = re.sub(r"\'ll", " will ", text)
    text = re.sub(r",", " ", text)
    text = re.sub(r"\.", " ", text)
    text = re.sub(r"!", " ! ", text)
    text = re.sub(r"\/", " ", text)
    text = re.sub(r"\^", " ^ ", text)
    text = re.sub(r"\+", " + ", text)
    text = re.sub(r"\-", " - ", text)
    text = re.sub(r"\=", " = ", text)
    text = re.sub(r"'", " ", text)
    text = re.sub(r"(\d+)(k)", r"\g<1>000", text)
    text = re.sub(r":", " : ", text)
    text = re.sub(r" e g ", " eg ", text)
    text = re.sub(r" b g ", " bg ", text)
    text = re.sub(r" u s ", " american ", text)
    text = re.sub(r"\0s", "0", text)
    text = re.sub(r" 9 11 ", "911", text)
    text = re.sub(r"e - mail", "email", text)
    text = re.sub(r"j k", "jk", text)
    text = re.sub(r"\s{2,}", " ", text)
    '''

    text = text.split()

    return text


def make_w2v_embeddings(df, embedding_dim, empty_w2v):  # 将词转化为词向量
    vocabs = {}  # 词序号
    vocabs_cnt = 0  # 词个数计数器

    vocabs_not_w2v = {}  # 无法用词向量表示的词
    vocabs_not_w2v_cnt = 0  # 无法用词向量表示的词个数计数器

    # 停用词
    stops = set(open('data/stopwords.txt').read().strip().split('\n'))

    # 加载词向量
    print("Loading word2vec model(it may takes 2-3 mins) ...")

    if empty_w2v:  # 若没有预训练好的词向量
        word2vec = {}
    else:
        word2vec = KeyedVectors.load("./Word Embedding/Word60.model")  # 使用10G中文维基百科训练好的词向量
        # 可以直接用训练集训练一个词向量。或者随机初始化词向量，然后伴随网络训练。
    for index, row in df.iterrows():
        # 打印处理进度
        if index != 0 and index % 1000 == 0:
            print("{:,} sentences embedded.".format(index), flush=True)

        for question in ['question1', 'question2']:
            q2n = []  # q2n -> question to numbers representation
            words = text_to_word_list(row[question])

            '''
            tempt = []  # 增加同义词
            for w in set(words):
                w_similar = word2vec.most_similar(w)[0][0]
                if w_similar not in words and w_similar not in tempt:
                    tempt.append(w_similar)
            words += tempt
            '''

            for word in words:
                if word in stops:  # 去停用词
                    continue
                if word not in word2vec and word not in vocabs_not_w2v:  # OOV的词放入不能用词向量表示的字典中，value为1
                    vocabs_not_w2v_cnt += 1
                    vocabs_not_w2v[word] = 1
                if word not in vocabs:  # 非OOV词，提取出对应的id
                    vocabs_cnt += 1
                    vocabs[word] = vocabs_cnt
                    q2n.append(vocabs_cnt)
                else:
                    q2n.append(vocabs[word])
            df.at[index, question + '_n'] = q2n

    embeddings = 1 * np.random.randn(len(vocabs) + 1, embedding_dim)  # 随机初始化一个形状为[全部词个数，词向量维度]的矩阵
    '''
    词1 [a1, a2, a3, ..., a60]
    词2 [b1, b2, b3, ..., b60]
    词3 [c1, c2, c3, ..., c60]
    '''
    embeddings[0] = 0  # 第一行用0填充，因为不存在index为0的词

    for index in vocabs:
        vocab_word = vocabs[index]
        if vocab_word in word2vec:
            embeddings[index] = word2vec[vocab_word]
    del word2vec

    return df, embeddings


def split_and_zero_padding(df, max_seq_length):  # 调整tokens长度

    # 训练集矩阵转换成字典
    X = {'left': df['question1_n'], 'right': df['question2_n']}

    # 调整到规定长度
    for dataset, side in itertools.product([X], ['left', 'right']):
        dataset[side] = pad_sequences(dataset[side], padding='pre', truncating='post', maxlen=max_seq_length)

    return dataset


class ManDist(Layer):  # 封装成keras层的曼哈顿距离计算

    # 初始化ManDist层，此时不需要任何参数输入
    def __init__(self, **kwargs):
        self.result = None
        super(ManDist, self).__init__(**kwargs)

    # 自动建立ManDist层
    def build(self, input_shape):
        super(ManDist, self).build(input_shape)

    # 计算曼哈顿距离
    def call(self, x, **kwargs):
        self.result = K.exp(-K.sum(K.abs(x[0] - x[1]), axis=1, keepdims=True))
        return self.result

    # 返回结果
    def compute_output_shape(self, input_shape):
        return K.int_shape(self.result)


class MashiDist(Layer):  # 封装成keras层的马氏距离计算

    # 初始化MashiDist层，此时不需要任何参数输入
    def __init__(self, **kwargs):
        self.result = None
        super(MashiDist, self).__init__(**kwargs)

    # 自动建立MashiDist层
    def build(self, input_shape):
        super(MashiDist, self).build(input_shape)

    # 计算马氏距离
    def call(self, x, **kwargs):
        X = np.vstack([x[0], x[1]])
        XT = np.transpose(X).astype(dtype='float32')
        self.result = pdist(XT, 'mahalanobis')
        return self.result

    # 返回结果
    def compute_output_shape(self, input_shape):
        return K.int_shape(self.result)