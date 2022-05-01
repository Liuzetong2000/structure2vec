from __future__ import print_function

import os
import sys
import numpy as np
import torch
import random
from torch.autograd import Variable
from torch.nn.parameter import Parameter
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from tqdm import tqdm

from s2v_lib import S2VLIB

def is_cuda_float(mat):
    version = get_torch_version()
    if version >= 0.4:
        return mat.is_cuda
    return type(mat) is torch.cuda.FloatTensor

def to_scalar(mat):
    version = get_torch_version()
    if version >= 0.4:
        return mat.item()
    return mat.data.cpu().numpy()[0]
 
def get_torch_version():
    return float('.'.join(torch.__version__.split('.')[0:2]))

def glorot_uniform(t):
    if len(t.size()) == 2:  #size()统计矩阵元素个数
        fan_in, fan_out = t.size()
    elif len(t.size()) == 3:
        # out_ch, in_ch, kernel for Conv 1
        fan_in = t.size()[1] * t.size()[2]       ####.size()[1] ？？？？？？
        fan_out = t.size()[0] * t.size()[2]
    else:
        fan_in = np.prod(t.size()) #np.prod()计算所有元素的乘积
        fan_out = np.prod(t.size())

    limit = np.sqrt(6.0 / (fan_in + fan_out))
    t.uniform_(-limit, limit)

def _param_init(m):
    if isinstance(m, Parameter): #如果m与Parameter类型相同则为1
        glorot_uniform(m.data)
    elif isinstance(m, nn.Linear):
        m.bias.data.zero_()
        glorot_uniform(m.weight.data)

def weights_init(m):
    for p in m.modules():
        if isinstance(p, nn.ParameterList):
            for pp in p:
                _param_init(pp)
        else:
            _param_init(p)

    for name, p in m.named_parameters():
        if not '.' in name: # top-level parameters
            _param_init(p)

class MySpMM(torch.autograd.Function):

    @staticmethod
    def forward(ctx, sp_mat, dense_mat):
        ctx.save_for_backward(sp_mat, dense_mat)

        return torch.mm(sp_mat, dense_mat)

    @staticmethod
    def backward(ctx, grad_output):        
        sp_mat, dense_mat = ctx.saved_variables
        grad_matrix1 = grad_matrix2 = None

        assert not ctx.needs_input_grad[0]
        if ctx.needs_input_grad[1]:
            grad_matrix2 = Variable(torch.mm(sp_mat.data.t(), grad_output.data))
        
        return grad_matrix1, grad_matrix2

def gnn_spmm(sp_mat, dense_mat):
    return MySpMM.apply(sp_mat, dense_mat)
