"""
=================================================================================
ASCET Tool (V14) 用于修复
1.非标参数参与检测
2.formula ident != identity
=================================================================================


系统概述:
    这是一个基于检索增强生成(RAG)技术的ASCET嵌入式软件代码审查系统。
    该系统结合了传统规则检查和AI智能分析，能够自动提取ASCET项目数据，
    执行多层次代码质量检查，并生成详细的审查报告。V12版本特别优化了
    多AI模型适配能力和Token统计功能。


RAG系统架构:
    1. 知识库管理 (HistoricalCaseRetriever)
       - 向量化存储历史案例
       - FAISS索引快速检索
       - 智能相似度匹配
       - 位置变量映射错误专项案例库
    
    2. 嵌入向量生成 (EmbeddingGenerator)
       - 文本向量化处理
       - 缓存机制优化性能
       - 率限制和重试机制
       - 向量有效性验证
    
    3. AI分析器 (RAGEnhancedAIReviewer)
       - 多模型配置管理
       - 历史案例检索集成
       - 上下文增强提示词构建
       - 流式和标准响应处理

核心组件详解:

1. RateLimiter 类:
   - 令牌桶算法实现API限流
   - 防止API调用超频
   - 支持突发请求处理

2. EmbeddingGenerator 类:
   - 文本嵌入向量生成
   - 本地缓存机制
   - 自动重试和错误处理
   - 向量质量验证

3. HistoricalCaseRetriever 类:
   - 历史案例库管理
   - 向量检索和相似度计算
   - 专门针对位置变量映射错误
   - FAISS索引优化查询性能

4. AscetCodeExtractor 类:
   - ASCET COM接口集成
   - 代码提取和方法分析
   - 引用类发现和代码获取
   - XML导出和参数映射提取

5. RAGEnhancedAIReviewer 类:
   - 统一多模型接口
   - RAG增强提示词生成
   - 历史案例格式化和集成
   - 推理过程处理(支持o1等推理模型)

6. RAGEnhancedCodeReviewer 类:
   - 主要业务逻辑协调
   - 规则检查执行
   - AI分析调用
   - 报告生成和格式化

代码审查功能:

基础规则检查:
- 未使用变量检测
- 变量赋值一致性检查  
- 信号范围问题检测
- 复杂条件语句分析
- 参数映射验证
- 重复条件检查
- 无限循环检测
- 精度/分辨率问题检查
  * uint32乘法溢出  
  * uint32加法位移精度丢失


AI深度分析(RAG增强):
- 位置变量映射错误检测(FL/FR/RL/RR)
- 返回值变量名称一致性检查
- 代码逻辑合理性分析
- 潜在缺陷模式识别
- 历史案例对比分析
- 上下文感知的问题定位

参数映射分析:
- XML文件解析和参数提取
- Local/Imported参数映射验证
- 常量参数识别和过滤
- 多依赖关系处理
- 浮点数精度容差比较
- 未映射参数检测

变量名称一致性:
- ASCET Methods提取和分析
- 方法名与返回变量匹配检查
- 位置标识一致性验证
- Return语句分析

工作流程:

阶段一: 数据准备
├── ASCET连接和代码提取
├── JSON信号定义加载
├── 引用类发现和代码获取
├── Methods信息提取
├── 参数映射XML解析
└── 数据验证和预处理

阶段二: 规则检查
├── 变量使用情况统一扫描
├── 信号范围和类型检查
├── 精度和分辨率问题检测
├── 参数映射一致性验证
├── 复杂度和质量指标计算
└── 基础问题汇总和分类

阶段三: AI分析(RAG增强)
├── 问题描述和代码上下文准备
├── 历史案例库查询和检索
├── 相似案例格式化和整合
├── RAG增强提示词构建
├── 多模型AI分析调用
├── 推理过程处理和解析
└── AI分析结果提取和验证

阶段四: 报告生成
├── 规则检查结果格式化
├── AI分析结果整合
├── 参数映射统计报告
├── 变量名称一致性报告  
├── Token使用统计
├── Markdown格式报告生成
└── 错误统计JSON输出

技术优势:

1. RAG技术集成:
   - 历史经验复用,提高分析准确性
   - 领域知识积累,减少误报率
   - 案例驱动分析,增强可解释性

2. 多模型支持:
   - 统一配置接口,简化模型切换
   - 自动推理处理,支持最新AI模型
   - 成本优化,根据需求选择合适模型

3. 精确Token统计:
   - 实时成本监控
   - API调用优化
   - 预算控制和告警

4. 性能优化:
   - 向量缓存机制
   - 批量数据处理
   - 并发请求控制
   - 内存使用优化

输出格式:

1. Markdown审查报告:
   - 执行摘要和统计信息
   - 规则检查详细结果  
   - AI分析结果(支持思考过程折叠)
   - 参数映射分析报告
   - Token使用统计

2. JSON错误统计:
   - 结构化错误数据
   - 严重程度分类
   - 详细错误描述
   - 位置和上下文信息

3. 性能和成本报告:
   - API调用统计
   - Token消耗分析
   - 成本估算
   - 性能指标

配置要求:

必需配置:
- class_path: ASCET项目类路径
- json_file_path: JSON信号定义文件
- deepseek_api_key: AI模型API密钥
- embedding_api_key: 向量化API密钥

```

兼容性说明:
- 向后兼容V11版本的核心接口
- 保持与AscetAgentv5的错误统计格式一致
- 支持现有知识库和配置文件
- 平滑升级路径,无需大幅修改调用代码


更新日志:
V13 更新日志:
- 添加analyze_parameter_name_consistency 函数的作用是数据收集和预处理，
为AI进行参数映射名称一致性检测做准备。具体功能包括：
1. 收集映射关系数据

从JSON信号定义中提取imported parameter和local parameter的信息
从XML参数映射中构建imported parameter → local parameter的依赖关系

2. 过滤和筛选

跳过常量参数引用（如引用parameter_constants中的参数）
只保留一对一的映射关系，跳过一对多映射（因为一对多映射匹配关系难以界定）
确保两个参数都在JSON定义中存在

3. 数据格式化

为每个映射对准备详细信息：

参数名称
参数属性（min, max, formula等）
XML文件信息
形式名称等



4. 统计信息初始化

初始化param_name_consistency_statistics统计数据
记录检查的映射对数量、分析状态等

5. 为AI分析做准备

将处理好的映射对存储到self.parameter_mapping_pairs
这些数据后续会被_prepare_parameter_mapping_context()方法格式化成AI提示词的一部分


V12 :
- 新增多AI模型支持
- 集成统一模型配置和响应处理模块
- 增强Token统计和成本监控功能
- 优化RAG检索算法和案例匹配
- 改进浮点数精度问题检测
- 改进错误统计和报告格式

V11:
- RAG系统基础架构
- 历史案例库建设
- 向量检索优化
- 基础规则检查完善


=================================================================================
"""

import os
import json
import re
import time
import random
import hashlib
import pickle
import numpy as np
import math
from typing import List, Dict, Any, Optional, Tuple
import requests
import faiss
from pathlib import Path
from tqdm import tqdm
from win32com.client import Dispatch
from datetime import datetime
import xml.etree.ElementTree as ET
import shutil
import glob
import sys
import traceback

#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# ==================== 模型适配器============================
from src.ai_core.model_config import ModelConfig, create_model_config, list_supported_models, REASONING_SUPPORTED_MODELS
from src.ai_core.response_handler import ResponseHandler, create_response_handler, process_model_response
# ==================== 统一Token统计系统 ====================
try:
    from src.ai_core.token_tracker import global_token_tracker, track_response, get_token_summary, reset_token_tracker
    print("Token Counter ok")
except ImportError as e:
    print(f"Token Counter error: {e}")

# ==================== RAG检索模块 ====================

class RateLimiter:
    def __init__(self, rate=60, per=60, burst=10):
        self.rate = rate    # 每 'per' 秒允许的请求数
        self.per = per      # 时间周期(秒)
        self.burst = burst  # 最大突发请求数
        self.tokens = burst # 初始令牌数
        self.last_time = time.time()
        
    def acquire(self):
        """获取令牌，如果没有立即可用的令牌，则等待"""
        current = time.time()
        elapsed = current - self.last_time
        self.last_time = current
        
        # 更新令牌
        self.tokens += elapsed * (self.rate / self.per)
        if self.tokens > self.burst:
            self.tokens = self.burst
        
        # 如果没有足够的令牌，等待
        if self.tokens < 1:
            wait_time = (1 - self.tokens) * (self.per / self.rate)
            time.sleep(wait_time)
            self.tokens = 0
        else:
            self.tokens -= 1


class EmbeddingGenerator:
    """嵌入向量生成器 - 用于RAG检索"""
    
    def __init__(self, api_key: str, 
                 api_url: str = "http://10.161.112.104:3000/v1/embeddings", 
                 model: str = "text-embedding-3-small",
                 cache_dir: str = "embedding_cache"):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.cache_dir = cache_dir
        self.rate_limiter = RateLimiter(rate=15, per=60, burst=3)
        
        # 创建缓存目录
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, text: str) -> str:
        """获取缓存文件路径"""
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.pkl")
    
    def _check_cache(self, text: str) -> Optional[List[float]]:
        """检查缓存中是否存在嵌入向量"""
        cache_path = self._get_cache_path(text)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"读取缓存时出错: {e}")
        return None
    
    def _save_to_cache(self, text: str, embedding: List[float]) -> None:
        """将嵌入向量保存到缓存"""
        cache_path = self._get_cache_path(text)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(embedding, f)
        except Exception as e:
            print(f"保存缓存时出错: {e}")
    
    def create_embedding(self, text: str, max_retries: int = 3) -> Optional[List[float]]:
        """为单个文本创建嵌入向量"""
        # 先检查缓存
        cached = self._check_cache(text)
        if cached:
            return cached
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "input": [text],
            "model": self.model,
            "encoding_format": "float"
        }
        
        # 指数退避重试
        retry_delay = 1
        for attempt in range(max_retries):
            try:
                # 使用令牌桶限制请求频率
                self.rate_limiter.acquire()
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # ✅ 使用统一Token统计记录向量生成API调用
                    track_response(result, "向量生成", "embedding", f"文本长度: {len(text)} 字符")
                    
                    embedding = result["data"][0]["embedding"]
                    
                    # 验证嵌入向量的有效性
                    if self._validate_embedding(embedding):
                        # 保存到缓存
                        self._save_to_cache(text, embedding)
                        return embedding
                    else:
                        print(f"警告: 嵌入向量验证失败")
                        return None
                
                elif response.status_code == 429:
                    wait_time = retry_delay * (1.5 + random.random())
                    print(f"API调用限流，等待 {wait_time:.2f} 秒后重试...")
                    time.sleep(wait_time)
                    retry_delay *= 2
                else:
                    print(f"API调用错误: {response.status_code} - {response.text}")
                    break
            
            except Exception as e:
                print(f"创建嵌入向量时出错: {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (1.5 + random.random())
                    time.sleep(wait_time)
                    retry_delay *= 2
        
        return None
    
    def _validate_embedding(self, embedding: List[float]) -> bool:
        """验证嵌入向量的有效性"""
        if not embedding:
            return False
        
        # 检查维度
        if len(embedding) != 1536:  # text-embedding-3-small的维度
            print(f"警告: 嵌入向量维度错误，期望1536，实际{len(embedding)}")
            return False
        
        # 检查是否包含异常值
        embedding_array = np.array(embedding)
        if np.any(np.isnan(embedding_array)) or np.any(np.isinf(embedding_array)):
            print("警告: 嵌入向量包含NaN或无穷大值")
            return False
        
        # 检查向量范数是否合理
        norm = np.linalg.norm(embedding_array)
        if norm == 0 or norm > 100:  # 合理的范数范围
            print(f"警告: 嵌入向量范数异常: {norm}")
            return False
        
        return True


class HistoricalCaseRetriever:
    """历史案例检索器 -"""
    
    def __init__(self, knowledge_base_path: str = "esdl_knowledge_base",
                 embedding_api_key: str = None):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.embedding_generator = EmbeddingGenerator(api_key=embedding_api_key) if embedding_api_key else None
        
        # 向量存储配置
        self.dimension = 1536  # text-embedding-3-small的维度
        self.index_path = self.knowledge_base_path / "faiss_index.bin"
        self.documents_path = self.knowledge_base_path / "documents.pkl"
        self.metadata_path = self.knowledge_base_path / "metadata.json"
        
        # 知识库数据
        self.knowledge_entries = []
        self.index = None
        self.metadata = {"total_entries": 0, "last_updated": None}
        
        # 位置变量映射错误相关的查询模板
        self.position_error_keywords = [
            "位置变量映射错误", "车轮位置变量赋值错误", "FL FR RL RR 映射错误",
            "抽象变量映射", "车轮变量交叉赋值", "位置映射不一致",
            "制动力分配位置错误", "车轮速度变量错误", "位置变量赋值",
            "Wrong Vehicle Position variable assignment", "wheel position mapping error",
            "FL FR RL RR assignment", "position variable mismatch"
        ]
        
        # 加载现有知识库
        self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """加载现有的知识库"""
        try:
            # 加载元数据
            if self.metadata_path.exists():
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                print(f"✓ 加载知识库元数据: {self.metadata.get('total_entries', 0)} 个条目")
            
            # 加载现有文档
            if self.documents_path.exists():
                with open(self.documents_path, "rb") as f:
                    self.knowledge_entries = pickle.load(f)
                print(f"✓ 加载知识库文档: {len(self.knowledge_entries)} 个条目")
            
            # 加载现有索引
            if self.index_path.exists():
                try:
                    self.index = faiss.read_index(str(self.index_path))
                    print(f"✓ 加载FAISS向量索引")
                except Exception as e:
                    print(f"⚠️ 加载FAISS索引失败: {e}")
                    self.index = None
            
        except Exception as e:
            print(f"⚠️ 加载知识库时出错: {e}")
            # 重置状态
            self.knowledge_entries = []
            self.index = None
            self.metadata = {"total_entries": 0, "last_updated": None}
    
    def search_similar_cases(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        搜索相似的历史案例
        
        Args:
            query_text (str): 查询文本（当前代码问题描述）
            top_k (int): 返回的相似案例数量
        
        Returns:
            List[Dict]: 相似案例列表
        """
        if not self.index or not self.embedding_generator:
            print("知识库未加载或嵌入生成器未初始化")
            return []
        
        # 生成查询向量
        query_embedding = self.embedding_generator.create_embedding(query_text)
        if not query_embedding:
            print("生成查询向量失败")
            return []
        
        try:
            # 搜索
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # 限制搜索数量不超过实际条目数
            actual_k = min(top_k, len(self.knowledge_entries))
            if actual_k == 0:
                return []
            
            distances, indices = self.index.search(query_vector, actual_k)
            
            # 返回结果
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx >= 0 and idx < len(self.knowledge_entries):
                    result = self.knowledge_entries[idx].copy()
                    result["similarity_score"] = float(distance)
                    result["rank"] = i + 1
                    results.append(result)
            
            return results
        
        except Exception as e:
            print(f"❌ 搜索历史案例时出错: {e}")
            return []
    
    def is_available(self) -> bool:
        """检查RAG系统是否可用"""
        return (self.index is not None and 
                len(self.knowledge_entries) > 0 and 
                self.embedding_generator is not None)


# ==================== ASCET代码提取模块 ====================

class AscetCodeExtractor:
    """ASCET代码提取器"""
    def __init__(self, version="6.1.4"):
        self.ascet = None
        self.db = None
        self.version = version
        
    def connect(self):
        """连接到ASCET并获取当前数据库"""
        try:
            self.ascet = Dispatch(f"Ascet.Ascet.{self.version}")
            self.db = self.ascet.GetCurrentDataBase()
            print(f"Successfully connected to ASCET {self.version}")
            return True
        except Exception as e:
            print(f"Connection failed: {str(e)}")
            return False
            
    def extract_method_code(self, class_path, diagram_name='Main', method_name='calc'):
        """
        从特定类方法中提取代码
        Parameters:
            class_path (str): 类的完整路径（使用反斜杠分隔）
            diagram_name (str): 图表名称，默认为 'Main'
            method_name (str): 方法名称，默认为 'calc'
        Returns:
            tuple: (code: str or None, error: str or None)
        """
        try:
            # 自动去掉开头的反斜杠
            if class_path.startswith("\\"):
                class_path = class_path[1:]
                
            # 解析路径
            path_parts = class_path.split('\\')
            class_name = path_parts[-1]
            folder_path = '\\'.join(path_parts[:-1])
            
            # 获取类组件
            class_item = self.db.GetItemInFolder(class_name, folder_path)
            if not class_item:
                return None, f"未找到类: {class_name}"
                
            # 获取指定图表
            diagram = class_item.GetDiagramWithName(diagram_name)
            if not diagram:
                return None, f"未找到图表: {diagram_name}"
                
            # 获取指定方法
            method = diagram.GetMethod(method_name)
            if not method:
                return None, f"未找到方法: {method_name}"
                
            # 提取并返回代码
            code = method.GetCode()
            return code, None
        except Exception as e:
            return None, str(e)

    def discover_reference_classes(self, class_path):
        """
        发现类中所有引用的其他类
        
        Args:
            class_path (str): 要分析的类路径
        
        Returns:
            list: 引用类信息列表 [{'element_name': str, 'ref_class_name': str, 'ref_class_path': str}]
        """
        try:
            # 获取类对象
            class_obj = self._get_class_object(class_path)
            if not class_obj:
                return []
            
            # 获取所有模型元素
            if not hasattr(class_obj, 'GetAllModelElements'):
                return []
            
            get_elements_attr = getattr(class_obj, 'GetAllModelElements')
            all_elements = get_elements_attr() if callable(get_elements_attr) else get_elements_attr
            
            if not all_elements:
                return []
            
            references = []
            
            # 遍历所有元素
            for i, element in enumerate(all_elements, 1):
                try:
                    if not element:
                        continue
                    
                    element_name = element.GetName()
                    
                    # 检查是否有引用类
                    if hasattr(element, 'GetRepresentedClass'):
                        represented_class = element.GetRepresentedClass()
                        
                        if represented_class:
                            # 检查是否是类引用
                            is_class = False
                            if hasattr(represented_class, 'IsClass'):
                                try:
                                    is_class = represented_class.IsClass()
                                except:
                                    continue
                            
                            if is_class:
                                ref_class_name = represented_class.GetName()
                                
                                # 获取引用类路径
                                if hasattr(represented_class, 'GetNameWithPath'):
                                    ref_class_path = represented_class.GetNameWithPath()
                                    if ref_class_path.startswith('\\'):
                                        ref_class_path = ref_class_path[1:]
                                else:
                                    ref_class_path = ref_class_name
                                
                                references.append({
                                    'element_name': element_name,
                                    'ref_class_name': ref_class_name,
                                    'ref_class_path': ref_class_path
                                })
                
                except Exception as e:
                    continue
            
            return references
            
        except Exception as e:
            print(f"发现引用类失败: {str(e)}")
            return []

    def extract_reference_codes(self, class_path, diagram_name='Main', method_name='calc'):
        """
        发现引用类并提取代码
        
        Args:
            class_path (str): 要分析的类路径
            diagram_name (str): 图表名称，默认"Main"
            method_name (str): 方法名称，默认"calc"
        
        Returns:
            dict: {
                'references': [引用信息],
                'codes': {元素名: 代码信息},
                'summary': {统计信息}
            }
        """
        # 步骤1：发现引用类
        references = self.discover_reference_classes(class_path)
        
        if not references:
            return {
                'references': [],
                'codes': {},
                'summary': {'total_refs': 0, 'success_extractions': 0, 'failed_extractions': 0}
            }
        
        # 步骤2：提取每个引用类的代码
        codes = {}
        success_count = 0
        failed_count = 0
        
        for i, ref in enumerate(references, 1):
            element_name = ref['element_name']
            ref_class_path = ref['ref_class_path']
            ref_class_name = ref['ref_class_name']
            
            code, error = self.extract_method_code(ref_class_path, diagram_name, method_name)
            
            if code and not error:
                codes[element_name] = {
                    'ref_class_name': ref_class_name,
                    'ref_class_path': ref_class_path,
                    'method_name': method_name,
                    'code': code,
                    'code_length': len(code)
                }
                success_count += 1
            else:
                codes[element_name] = {
                    'ref_class_name': ref_class_name,
                    'ref_class_path': ref_class_path,
                    'method_name': method_name,
                    'code': None,
                    'error': error or '代码获取失败'
                }
                failed_count += 1
        
        result = {
            'references': references,
            'codes': codes,
            'summary': {
                'total_refs': len(references),
                'success_extractions': success_count,
                'failed_extractions': failed_count
            }
        }
        
        return result



    
    def _get_class_object(self, class_path):
        """内部函数：获取类对象"""
        class_item = None
        
        # 自动去掉开头的反斜杠
        if class_path.startswith("\\"):
            class_path = class_path[1:]
        
        # 方法1：直接使用GetItem (适用于简单路径)
        try:
            class_item = self.db.GetItem(class_path)
            if class_item:
                return class_item
        except:
            pass
        
        # 方法2：路径解析
        try:
            # 规范化路径
            normalized_path = class_path.replace('/', '\\')
            if normalized_path.startswith('\\'):
                normalized_path = normalized_path[1:]
            
            # 解析路径
            path_parts = normalized_path.split('\\')
            class_name = path_parts[-1]
            
            if len(path_parts) > 1:
                # 有文件夹路径
                folder_path = '\\'.join(path_parts[:-1])
                class_item = self.db.GetItemInFolder(class_name, folder_path)
            else:
                # 只有类名
                class_item = self.db.GetItem(class_name)
        except Exception as e:
            pass
        
        return class_item
    
    def _get_method_info(self, method):
        """
        通用的ASCET方法信息获取函数
        Parameters:
            method: ASCET方法对象
        Returns:
            tuple: (method_info_dict, error)
        """
        try:
            method_info = {}
            
            # 尝试获取方法名称
            try:
                if hasattr(method, 'Name'):
                    method_info['name'] = method.Name
                elif hasattr(method, 'GetName'):
                    method_info['name'] = method.GetName()
                else:
                    # 如果没有直接的Name属性，尝试通过GetValue方式获取
                    di = method.GetValue() if hasattr(method, 'GetValue') else None
                    if di and hasattr(di, 'GetStringValue'):
                        method_info['name'] = di.GetStringValue()
                    else:
                        method_info['name'] = f"Method_{id(method)}"
            except:
                method_info['name'] = f"Method_{id(method)}"
            
            # 尝试获取方法代码
            try:
                if hasattr(method, 'GetCode'):
                    method_info['code'] = method.GetCode()
                else:
                    method_info['code'] = None
                    method_info['code_error'] = "方法不支持GetCode()"
            except Exception as e:
                method_info['code'] = None
                method_info['code_error'] = f"获取代码失败: {e}"
            
            return method_info, None
            
        except Exception as e:
            return None, f"获取方法信息失败: {e}"
    
    def get_all_methods_for_variable_analysis(self, class_path, diagram_name='Main'):
        """
        专门为变量使用分析获取所有methods（包含init，排除calc）
        
        Args:
            class_path (str): 类的完整路径
            diagram_name (str): 图表名称，默认为'Main'
        
        Returns:
            dict: {method_name: method_code} 或 {} 如果失败
        """
        try:
            # 自动去掉开头的反斜杠
            if class_path.startswith("\\"):
                class_path = class_path[1:]
            
            # 解析路径
            path_parts = class_path.split('\\')
            class_name = path_parts[-1]
            folder_path = '\\'.join(path_parts[:-1])
            
            # 获取类组件
            class_item = self.db.GetItemInFolder(class_name, folder_path)
            if not class_item:
                return {}
            
            # 获取指定图表
            diagram = class_item.GetDiagramWithName(diagram_name)
            if not diagram:
                return {}
            
            # 获取所有方法
            all_methods = diagram.GetAllMethods()
            if not all_methods:
                return {}
            
            methods_dict = {}
            for method in all_methods:
                method_info, error = self._get_method_info(method)
                if method_info and 'error' not in method_info and method_info.get('code'):
                    method_name = method_info['name']
                    # 只排除calc方法，保留init和所有其他方法
                    if method_name.lower() != 'calc':
                        methods_dict[method_name] = method_info['code']
            
            return methods_dict
            
        except Exception:
            return {}


    def get_all_methods_in_diagram(self, class_path, diagram_name='Main'):
        """
        获取指定diagram中的所有methods
        Parameters:
            class_path (str): 类的完整路径（使用反斜杠分隔）
            diagram_name (str): 图表名称，默认为 'Main'
        Returns:
            tuple: (methods_info: list or None, error: str or None)
                methods_info是一个字典列表，每个字典包含方法名和代码
        """
        
        # 自动去掉开头的反斜杠
        if class_path.startswith("\\"):
            class_path = class_path[1:]
        
        # 解析路径
        path_parts = class_path.split('\\')
        class_name = path_parts[-1]
        folder_path = '\\'.join(path_parts[:-1])
        
        # 获取类组件
        class_item = self.db.GetItemInFolder(class_name, folder_path)
        if not class_item:
            return None, f"未找到类: {class_name}"
        
        # 获取指定图表
        diagram = class_item.GetDiagramWithName(diagram_name)
        if not diagram:
            return None, f"未找到图表: {diagram_name}"
        
        # 获取所有方法
        all_methods = diagram.GetAllMethods()
        if not all_methods:
            return [], f"图表 {diagram_name} 中没有找到任何方法"
        
        methods_info = []
        for i, method in enumerate(all_methods):
            method_info, error = self._get_method_info(method)
            if method_info:
                # 过滤掉名为"calc"的方法
                if method_info['name'].lower() == 'calc':
                    continue
                if method_info['name'].lower() == 'init':
                    continue
                
                methods_info.append(method_info)
            else:
                # 如果某个方法处理失败，记录错误但继续处理其他方法
                error_info = {
                    'name': f"Method_{i}",
                    'code': None,
                    'error': error
                }
                methods_info.append(error_info)
        
        return methods_info, None
    
    def extract_all_methods_code(self, class_path, diagram_name='Main'):
        """
        提取指定diagram中所有methods的代码（只返回代码字典）
        Parameters:
            class_path (str): 类的完整路径（使用反斜杠分隔）
            diagram_name (str): 图表名称，默认为 'Main'
        Returns:
            tuple: (methods_code: dict or None, error: str or None)
                methods_code是一个字典，键为方法名，值为代码字符串
        """
        methods_info, error = self.get_all_methods_in_diagram(class_path, diagram_name)
        
        if error:
            return None, error
        
        methods_code = {}
        for method in methods_info:
            if 'error' not in method and method['code'] is not None:
                methods_code[method['name']] = method['code']
        
        return methods_code, None

    def export_class_to_xml(self, class_path, output_file_path, include_references=False):
        """
        将指定的ASCET类导出为XML文件（新增：用于参数映射提取）
        Parameters:
            class_path (str): 类的完整路径（使用反斜杠分隔）
            output_file_path (str): 输出XML文件的完整路径
            include_references (bool): 是否包含引用的组件，默认为False
        Returns:
            tuple: (success, error_message)
        """
        # 自动去掉开头的反斜杠
        if class_path.startswith("\\"):
            class_path = class_path[1:]
        
        # 解析路径
        path_parts = class_path.split('\\')
        class_name = path_parts[-1]
        folder_path = '\\'.join(path_parts[:-1])
        
        try:
            # 获取类组件
            class_item = self.db.GetItemInFolder(class_name, folder_path)
            if not class_item:
                return False, f"未找到类: {class_name} (在 '{folder_path}' 下)"
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file_path)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except Exception as e:
                    return False, f"无法创建输出目录 {output_dir}: {e}"
            
            # 调用ASCET API导出XML
            success = class_item.ExportXMLToFile(output_file_path, include_references)
            
            if success:
                return True, None
            else:
                return False, "ExportXMLToFile 方法返回 False，导出失败"
                
        except Exception as e:
            error_msg = f"导出XML时发生异常: {e}"
            return False, error_msg
            
    def disconnect(self):
        """断开与ASCET的连接"""
        if self.ascet:
            try:
                self.ascet.DisconnectFromTool()
                print("Disconnected from ASCET")
            except Exception as e:
                print(f"Error disconnecting: {str(e)}")


# ==================== RAG增强的AI审查器 ====================


class RAGEnhancedAIReviewer:
    """RAG的AI审查器（使用独立的模型配置和响应处理模块）"""
    
    def __init__(self, deepseek_api_key: str, embedding_api_key: str,
                 deepseek_api_url: str = "http://10.161.112.104:3000/v1/chat/completions",
                 knowledge_base_path: str = "esdl_knowledge_base",
                 model_type: str = "gpt-oss-120b"):
        
        # 使用导入的模块创建模型配置和响应处理器
        self.model_config = create_model_config(model_type)
        self.response_handler = create_response_handler(model_type)
        
        # AI生成相关配置
        self.deepseek_api_key = deepseek_api_key
        self.deepseek_api_url = deepseek_api_url
        self.proxies = {'http': None, 'https': None}
        self.base_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {deepseek_api_key}"
        }
        
        # RAG检索器
        self.case_retriever = HistoricalCaseRetriever(
            knowledge_base_path=knowledge_base_path,
            embedding_api_key=embedding_api_key
        )
        
        # 系统提示词模板
        self.system_prompt_template = """You are an expert automotive software code reviewer with deep knowledge of ASCET, embedded systems, vehicle dynamics, and safety-critical automotive software. You excel at detecting position-related variable assignment errors, automotive-specific logic issues, and performing detailed coverage analysis."""
        
        print(f"🤖 RAG增强AI审查器初始化 - 模型: {self.model_config.get_model_name()}")
        if self.model_config.supports_reasoning():
            print(f"   推理支持: ✅ (字段: {self.model_config.get_reasoning_field()})")
        else:
            print(f"   推理支持: ❌")
    
    def switch_model(self, model_type: str):
        """动态切换模型"""
        try:
            # 使用导入的模块重新创建配置和处理器
            self.model_config = create_model_config(model_type)
            self.response_handler = create_response_handler(model_type)
            print(f"🔄 已切换到模型: {self.model_config.get_model_name()}")
            return True
        except Exception as e:
            print(f"❌ 模型切换失败: {e}")
            return False
    
    def generate_query_for_retrieval(self, main_code_str: str, issues_str: str, 
                                   class_path: str = "") -> str:
        """
        生成用于检索历史案例的查询文本
        
        Args:
            main_code_str (str): 主要代码内容
            issues_str (str): 发现的问题描述
            class_path (str): 类路径
        
        Returns:
            str: 查询文本
        """
        # 构建查询文本，重点关注位置变量映射错误
        query_parts = []
        
        # 添加错误类别（专门针对位置变量映射错误）
        query_parts.append(f"[ERROR_CATEGORY]: 位置变量映射错误")
        
        # 添加类路径信息
        if class_path:
            query_parts.append(f"[CLASS_PATH]: {class_path}")
        
        # 检查是否包含位置变量映射相关问题
        if issues_str and issues_str != "No issues found":
            # 过滤出位置变量相关的问题
            position_related = self._filter_position_issues(issues_str)
            if position_related:
                query_parts.append(f"[DETECTED_ISSUES]: {position_related}")
            else:
                query_parts.append(f"[DETECTED_ISSUES]: {issues_str}")
        
        # 从代码中提取位置变量特征
        position_features = self._extract_position_features(main_code_str)
        if position_features:
            query_parts.append(f"[POSITION_FEATURES]: {position_features}")
        
        # 添加位置变量映射错误的通用描述
        query_parts.append("[ERROR_DESCRIPTION]: 车轮位置变量映射错误或赋值不一致")
        query_parts.append("[KEYWORDS]: FL FR RL RR 位置变量 映射错误 车轮变量 抽象映射")
        
        return "\n".join(query_parts)
    
    def _filter_position_issues(self, issues_str: str) -> str:
        """过滤出位置变量相关的问题"""
        position_keywords = [
            "position", "位置", "FL", "FR", "RL", "RR", 
            "wheel", "车轮", "mapping", "映射", "variable", "变量",
            "Cross Assignment", "交叉赋值"
        ]
        
        issues_lines = issues_str.split('\n')
        position_issues = []
        
        for line in issues_lines:
            if any(keyword.lower() in line.lower() for keyword in position_keywords):
                position_issues.append(line.strip())
        
        return '\n'.join(position_issues[:3])  # 最多3个相关问题
    
    def _extract_position_features(self, code_str: str) -> str:
        """从代码中提取位置变量特征"""
        features = []
        
        # 检查车轮位置变量
        wheel_positions = ["FL", "FR", "RL", "RR"]
        found_positions = []
        for pos in wheel_positions:
            if pos in code_str:
                found_positions.append(pos)
        
        if found_positions:
            features.append(f"涉及车轮位置: {', '.join(found_positions)}")
        
        # 检查抽象变量
        abstract_vars = ["XX", "XY", "YY", "YX"]
        found_abstract = []
        for var in abstract_vars:
            if var in code_str:
                found_abstract.append(var)
        
        if found_abstract:
            features.append(f"抽象变量: {', '.join(found_abstract)}")
        
        # 检查映射模式
        mapping_patterns = re.findall(r'([FL|FR|RL|RR]).*=.*([FL|FR|RL|RR])', code_str)
        if mapping_patterns:
            features.append(f"位置映射: {len(mapping_patterns)}处")
        
        # 检查制动相关变量
        if "MbTar" in code_str or "brake" in code_str.lower():
            features.append("制动控制相关")
        
        return "; ".join(features) if features else "通用位置变量分析"
    
    def format_historical_cases(self, similar_cases: List[Dict[str, Any]]) -> str:
        """
        格式化历史案例用于提示词
        
        Args:
            similar_cases (List[Dict]): 检索到的相似案例
        
        Returns:
            str: 格式化的历史案例文本
        """
        if not similar_cases:
            return "暂无相关历史案例"
        
        formatted_cases = []
        formatted_cases.append(f"## 历史相似案例参考 ({len(similar_cases)}个案例)")
        formatted_cases.append("根据位置变量映射错误特征，以下是相关的历史错误案例，供分析参考：\n")
        
        for i, case in enumerate(similar_cases, 1):
            formatted_cases.append(f"### 案例 {i} (相似度分数: {case.get('similarity_score', 0):.3f})")
            formatted_cases.append(f"**类路径**: {case.get('class_path', '未知')}")
            formatted_cases.append(f"**错误类别**: {case.get('error_category', '未知')}")
            formatted_cases.append(f"**错误描述**: {case.get('error_description', '未知')}")
            
            # 添加代码片段（限制长度）
            if case.get('code_with_lines'):
                code_lines = case['code_with_lines'].split('\n')
                if len(code_lines) > 15:  # 如果代码太长，只显示前15行
                    display_code = '\n'.join(code_lines[:15]) + '\n... (代码已截断)'
                else:
                    display_code = case['code_with_lines']
                
                formatted_cases.append(f"**相关代码**:")
                formatted_cases.append("```c")
                formatted_cases.append(display_code)
                formatted_cases.append("```")
            
            formatted_cases.append("---")
        
        formatted_cases.append("**分析指导**: 请参考上述历史案例中的位置变量映射错误模式，分析当前代码是否存在类似问题。")
        formatted_cases.append("")
        
        return "\n".join(formatted_cases)
    
    def call_deepseek_with_rag(self, main_code_str: str, reference_codes_dict: Dict, 
                              signals_info: str, issues_str: str, class_path: str = "",
                              local_return_mappings: Dict = None):
        """
        使用RAG增强调用AI模型进行代码分析
        
        Args:
            main_code_str (str): 主代码（带行号）
            reference_codes_dict (Dict): 引用类代码字典
            signals_info (str): 信号信息
            issues_str (str): 规则检查发现的问题
            class_path (str): 类路径
            local_return_mappings (Dict): Methods映射信息
        
        Returns:
            str: AI分析结果
        """
        start_time = time.time()
        
        # 步骤1: 检索相似历史案例（优化版：专门针对位置变量映射错误）
        historical_cases = []
        if self.case_retriever.is_available():
            print("🔍 检索位置变量映射错误相关历史案例...")
            
            # 生成专门的检索查询
            retrieval_query = self.generate_query_for_retrieval(
                main_code_str, issues_str, class_path
            )
            
            # 执行检索
            historical_cases = self.case_retriever.search_similar_cases(
                retrieval_query, top_k=3
            )
            
            if historical_cases:
                print(f"✓ 找到 {len(historical_cases)} 个相似位置变量映射案例")
            else:
                print("ℹ️ 未找到相似位置变量映射案例")
        else:
            print("⚠️ RAG检索系统不可用，使用常规分析")
        
        # 步骤2: 构建增强提示词（传递local_return_mappings参数）
        base_prompt, code_prompt = self._build_rag_enhanced_prompt(
            main_code_str, reference_codes_dict, signals_info, 
            issues_str, historical_cases, local_return_mappings
        )
        
        # 步骤3: 调用AI模型
        return self._call_ai_api(base_prompt, code_prompt, start_time)
    
    def _prepare_methods_context(self, local_return_mappings: Dict = None):
        """准备ASCET Methods上下文信息（用于变量名称一致性检查）"""
        if not local_return_mappings:
            return "## ASCET Methods信息\n\n无可用的Methods数据\n"
        
        context_parts = []
        context_parts.append(f"## ASCET Methods信息（用于变量名称一致性检查）")
        context_parts.append(f"从ASCET GetAllMethods提取到 {len(local_return_mappings)} 个Methods（除calc和init外）：\n")
        
        for method_name, mappings in local_return_mappings.items():
            context_parts.append(f"### Method: {method_name}")
            
            # 显示return语句（通常每个method只有一个）
            return_statements = mappings.get('return_statements', [])
            if return_statements:
                for return_stmt in return_statements:
                    context_parts.append(f"- **Line {return_stmt['line']}**: `return {return_stmt['variable']};`")
            else:
                context_parts.append("- 无return语句")
            
            # 显示关键赋值语句（如果有的话）
            assignments = mappings.get('assignments', [])
            if assignments:
                context_parts.append("- 关键赋值:")
                for assignment in assignments[:2]:  # 最多显示2个赋值
                    context_parts.append(f"  - Line {assignment['line']}: `{assignment['left_variable']} = {assignment['right_variable']};`")
                if len(assignments) > 2:
                    context_parts.append(f"  - ... (还有 {len(assignments) - 2} 个赋值)")
            
            context_parts.append("")  # 空行分隔
        
        context_parts.append("### 变量名称一致性检查重点:")
        context_parts.append("- 检查方法名中的位置标识（FL/FR/RL/RR）是否与返回变量的位置标识匹配")
        context_parts.append("- 例如：`DeviationFL_Ori()` 应该返回包含 `FL` 的变量，而不是 `RL` 或其他位置")
        context_parts.append("- 重点关注方法名暗示的车轮位置与实际返回变量的不匹配情况")
        context_parts.append("")
        
        return '\n'.join(context_parts)
    
    def _build_rag_enhanced_prompt(self, main_code_str: str, reference_codes_dict: Dict,
                                  signals_info: str, issues_str: str, 
                                  historical_cases: List[Dict],
                                  local_return_mappings: Dict = None) -> Tuple[str, str]:
        """构建RAG增强的提示词（集成变量名称一致性检查）"""
        
        # 格式化历史案例
        historical_cases_text = self.format_historical_cases(historical_cases)
        
        # 准备引用类代码信息
        reference_context = self._prepare_reference_context(reference_codes_dict)
        
        # 准备ASCET Methods信息
        methods_context = self._prepare_methods_context(local_return_mappings)
        
        param_mapping_context = ""

        if hasattr(self, 'parameter_mapping_pairs') and self.parameter_mapping_pairs:
            param_mapping_context = self._prepare_parameter_mapping_context()
        else:
            param_mapping_context = "## 参数映射名称一致性检查\n\n无可用的参数映射数据\n"
        
       
        
        # 基础提示词（增加
        base_prompt = f"""你是一位汽车控制系统架构师，专门理解复杂的智能制动系统设计。




## 严格分析约束 - 必须遵守

1. **只分析具体代码问题** - 禁止理论讨论
2. **只关注实际错误** - 禁止设计建议 
3. **必须指出具体行号** - 禁止泛泛而谈
4. **参考历史案例** - 借鉴上述案例中的错误识别模式
5. **检查变量名称一致性** - 分析Methods中的变量命名是否合理

### 历史案例学习重点：
- 关注历史案例中的错误模式和识别方法
- 对比当前代码与历史案例的相似性
- 重点关注位置变量映射错误（FL/FR/RL/RR）

### 禁止行为（严格执行）：
1. **禁止推测**：不得基于假设分析问题
2. **禁止创造**：不得报告代码中不存在的问题
3. **禁止泛化**：不得从单个问题推广到整体架构
4. **禁止主观判断**：只报告明确的技术错误
5. **必须提供证据**：每个判断必须有证据支持

## 汽车专业知识补充（仅用于理解上下文）:
1. **动态力分配**: 根据驾驶条件实时调整每个车轮的制动力
2. **抽象控制层**: 使用抽象值进行计算，然后映射到具体车轮
3. **状态机控制**: 不同系统状态有不同的控制逻辑
4. **对角线参考策略**: 车轮间的相互参考和补偿机制
5. **制动力分配原理**: 基于车辆动力学的力分配策略

## 车轮位置命名规范（用于返回值变量名称一致性检查methods_context）:
- **FL**: Front Left (前左)
- **FR**: Front Right (前右) 
- **RL**: Rear Left (后左)
- **RR**: Rear Right (后右)

## 审查要求:
1. 用英文回复
2. 区分"设计复杂性"和"实际错误"
3. **重点参考历史案例进行模式识别**
4. **同时检查Methods中的变量名称一致性**
5. 只报告真正的错误，不报告设计选择


代码例子库：

**必须首先区分两种映射模式：**
1. **抽象映射模式**（正确，不报错）：
   ```
   Loc_MbTar_FL = object.MbTar_XX();  // XX是算法计算结果，不是固定车轮
   ````
   - XX/XY/YY/YX 是抽象计算值，根据控制逻辑动态映射到FL/FR/RL/RR
   - 这种映射是正确的软件分层设计，**禁止报错**

2. **直接映射模式**（需要检查）：
   ```
   if(MovDirRL == Lowering)  
   Phase_EachCorner_loc = EachCorner_FR_Cycle;  // 错误
   ```
   - 特征：直接赋值，条件位置与赋值位置不匹配
   - 这种才是真正的位置变量映射错误

**返回值变量名称映射错误检查示例：**
- 正确：`DeviationFL_Ori() return DeviationFL_Ori` - 方法名与返回变量匹配
- 错误：`DeviationFLFR_Ori() return DeviationRL_Ori` - 方法名暗示FLFR但返回RL
- 错误：`TargetHeight_FL_K1() return TargetHeight_RR_K1` - 方法名FL但返回RR
- 无需关注其他类似_U等无关位置变量




"""
        
        

        # 代码特定提示词
        code_specific_prompt = f"""


### 第一步：历史案例对比分析

1. **分析可能导致误报的点**
2. **重点关注位置变量映射错误**
3. **对比当前主类代码与上述历史案例，

### 第二步：错误类型筛选
**检查以下3类错误：**

1. **位置变量映射错误**: 主需要关注主类代码{main_code_str}和参考历史案例{historical_cases_text}
   - 对比当前代码与上述历史案例
   - 只关注methods_context中是否存在位置变量映射错误，无需关注main_code_str，param_mapping_context
   - 参考历史案例中的错误模式，导致错误的原因，或者误报错误的原因
   - 检查FL/FR/RL/RR位置变量赋值  
   
2. **返回值变量名称映射错误**（只关注ASCET Methods信息）:{methods_context}
   - 只关注methods_context 无需关注main_code_str，param_mapping_context
   - 方法名与返回变量位置不一致：如`DeviationFR_Ori()`但返回`DeviationRL_Ori`
   - 方法名暗示的车轮位置与实际返回变量的位置标识不匹配
   - 只检查除calc和init外的Methods，这些Methods通常只有一个return语句
    
3. **参数映射名称映射错误**（只关注参数映射信息）参数映射信息:{param_mapping_context}
   - 只关注param_mapping_context 无需关注main_code_str,methods_context
   - 检测-交叉映射：存在 imported parameterA→local parameterB 与 imported parameterB→local parameterA
   - 检查-两个映射参数之间名称是否核心功能语义不匹配，例如：P_iTAS_Distance4PressureIncrease→C_Distance4PressureIncrease，关注Distance4PressureIncrease这种核心内容.
   - 检测-位置参数映射错误
 

### 第三步：具体定位
**对每个发现的错误：**
- 指出准确行号
- 说明错误类型  
- 提供具体变量名和参数名
- 分析是否是误报，进行自我校验
- **对于变量名称和参数名称映射语义一致性错误，明确指出方法名和返回变量的不匹配**

### 第四步：验证确认
**最终确认标准：**
- 这是代码错误，不是设计选择？
- 我能指出具体行号？
- 对于Methods分析，是否确实存在命名语义不一致？
- 对于参数映射，是否确实存在命名语义不匹配？

## 输出格式要求：

严格按照下面的固定格式json模板，注意[]完整，简洁的将思考的过程和结果进行总结，简洁描述，只描述最关键的问题，若没有错误则为输出无错误：



```json
{{
  "错误类型": ["位置变量映射错误"],
  "状态": ["No Defect", "Defect"],
  "代码行号X": "列出具体行号",
  "理由": "代码行号X:xx，简洁描述错误，如果没有错误为空"
}}
```

```json
{{
  "错误类型": ["返回值变量名称映射错误"],
  "状态": ["No Defect", "Defect"], 
  "Methods问题": "如果发现Methods变量名称不一致，描述具体问题",
  "理由": "简洁描述：MethodsName：xxx,具体错误描述,如果没有错误为空"
}}
```

```json
{{
  "错误类型": ["参数名称映射错误"],
  "状态": ["No Defect", "Defect"],
  "理由":" 简洁描述有问题的Mappings："imported_paramxxx" -> "local_paramxxx",如果有错误，具体错误描述，如果没有错误为空"
}}
```

请严格按照此流程进行。"""
        
        return base_prompt, code_specific_prompt
    # 3. **参数映射错误**: .2. **返回值变量名称映射错误**:,1. 1. **位置变量映射错误**: 
    def _prepare_reference_context(self, reference_codes_dict):
        """准备引用类代码上下文信息"""
        if not reference_codes_dict:
            return "无引用类代码"
        
        context_parts = []
        context_parts.append(f"发现 {len(reference_codes_dict)} 个引用类，作为主类分析的上下文:")
        
        for element_name, code_info in reference_codes_dict.items():
            ref_class_name = code_info.get('ref_class_name', '未知')
            code = code_info.get('code')
            
            context_parts.append(f"\n### 引用类: {ref_class_name} (通过元素 {element_name} 引用)")
            
            if code:
                # 为引用类代码添加行号（简化版）
                lines = code.split('\n')[:10]  # 只显示前10行
                numbered_lines = []
                for i, line in enumerate(lines, 1):
                    numbered_lines.append(f"{i:>3}: {line}")
                
                context_parts.append(f"```c")
                context_parts.append('\n'.join(numbered_lines))
                if len(code.split('\n')) > 10:
                    context_parts.append("... (代码已截断)")
                context_parts.append(f"```")
            else:
                error = code_info.get('error', '未知错误')
                context_parts.append(f"代码提取失败: {error}")
        
        return '\n'.join(context_parts)
    
    def _call_ai_api(self, base_prompt: str, code_prompt: str, start_time: float) -> str:
        """
        调用AI API（使用导入的响应处理模块）
        """
        messages = [
            {"role": "system", "content": self.system_prompt_template},
            {"role": "user", "content": base_prompt},
            {"role": "user", "content": code_prompt}
        ]
        
        # 使用模型配置获取请求参数
        payload = self.model_config.get_request_params(messages)
        
        try:
            import json
            import os
            from datetime import datetime
            
            os.makedirs("Debug_Prompts", exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_filename = f"Debug_Prompts/prompt_{timestamp}.json"
            
            with open(debug_filename, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
                
            print(f" [DEBUG] Đã lưu payload gửi cho AI tại: {debug_filename}")
        except Exception as e:
            print(f" [DEBUG] Lỗi khi lưu prompt: {e}")


        try:
            response = requests.post(
                url=self.deepseek_api_url,
                json=payload,
                headers=self.base_headers,
                proxies=self.proxies,
                timeout=600
            )
            
            if response.status_code == 200:
                if self.model_config.is_streaming():
                    return self._process_streaming_response(response, start_time)
                else:
                    return self._process_standard_response(response, start_time)
            else:
                return f"AI API Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"AI API Request failed: {e}"
    
    def _process_standard_response(self, response, start_time):
        """处理标准（非流式）响应"""
        try:
            response_data = response.json()
            end_time = time.time()
            
            # 使用响应处理器处理完整响应
            processed_response = self.response_handler.process_complete_response(response_data)
            
            # 提取Token使用信息并记录
            usage_info = processed_response['usage_info']
            track_response(
                response_json=response_data,
                api_name="RAG增强分析",
                api_type=self.model_config.model_type,
                context="位置变量映射错误检测"
            )
            
            # 获取完整内容（包含格式化的推理过程）
            content = processed_response['complete_content']
            
            # 添加分析信息
            model_info = f"\n\n---\n**RAG增强分析**: 本次分析使用{self.model_config.get_model_name()}模型，参考了历史案例库，专门针对位置变量映射错误，分析耗时: {end_time - start_time:.2f}秒"
            
            if usage_info.get('reasoning_tokens', 0) > 0:
                model_info += f"，推理Token: {usage_info['reasoning_tokens']}"
                
            content += model_info
            
            return content
                
        except Exception as e:
            return f"Error processing standard response: {e}"
    
    def _process_streaming_response(self, response, start_time):
        """处理流式响应（主要用于DeepSeek）"""
        content = ""
        usage_data = None
        
        try:
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data.strip() == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data)
                            
                            # 提取内容
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                delta_content = delta.get('content')
                                if delta_content is not None:
                                    content += delta_content
                            
                            # 提取Token使用信息
                            if 'usage' in chunk:
                                usage_data = chunk['usage']
                                
                        except json.JSONDecodeError:
                            continue
            
            end_time = time.time()
            
            # 记录Token使用
            if usage_data:
                track_response(
                    response_json={"usage": usage_data},
                    api_name="RAG增强分析",
                    api_type=self.model_config.model_type,
                    context="位置变量映射错误检测"
                )
            
            # 对流式响应进行后处理（提取推理内容等）
            if self.model_config.supports_reasoning():
                # 构建标准响应格式用于处理
                mock_response = {
                    "choices": [{"message": {"content": content}}],
                    "usage": usage_data or {}
                }
                processed = self.response_handler.process_complete_response(mock_response)
                content = processed['complete_content']
            
            # 添加分析信息
            model_info = f"\n\n---\n**RAG增强分析**: 本次分析使用{self.model_config.get_model_name()}模型，参考了历史案例库，专门针对位置变量映射错误，分析耗时: {end_time - start_time:.2f}秒"
            content += model_info
            
            return content
                
        except Exception as e:
            return f"Error processing streaming response: {e}"
        
# ==================== 代码审查器 ====================

class RAGEnhancedCodeReviewer:
    """RAG增强的代码审查器 - 主要接口类（集成变量名称一致性检查到现有功能）"""
    
    def __init__(self, json_file_path: str, 
                 deepseek_api_key: str, 
                 embedding_api_key: str,
                 knowledge_base_path: str = "esdl_knowledge_base",
                 ascet_extractor=None, 
                 ascet_version: str = "6.1.4",
                 output_dir: str = None,
                 model_type: str = "gpt-oss-120b"):
        
        self.json_file_path = json_file_path
        self.json_data = None
        self.code_str = None
        self.issues = []
        self.class_name = None
        self.class_path = None
        
        # ASCET集成
        self.ascet_extractor = ascet_extractor
        self.ascet_version = ascet_version
        self.methods_info = {}
        self.local_return_mappings = {}
        self.output_dir = output_dir or "agent_reports"
        self.report_output_dir = self.output_dir
        # 引用类相关
        self.reference_analysis = None
        self.reference_codes_dict = {}
        
        # 参数映射相关
        self.parameter_mappings = []
        self.temp_xml_dir = r"C:\temp\xml_export_review"
        
        # XML映射统计
        self.xml_mapping_statistics = {
            'total_mappings': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'mismatched_parameters': 0,
            'unmapped_local_parameters': 0,
            'missing_imported_parameters': 0,
            'float_precision_issues_filtered': 0,
            'mapping_details': [],
            'noncalibration_imported_skipped': 0, 
        }
        
        # 变量名称一致性统计
        self.name_consistency_statistics = {
            'total_method_checks': 0,
            'ai_analysis_performed': False,
            'issues_found': 0,
            'high_severity_issues': 0,
            'medium_severity_issues': 0,
            'low_severity_issues': 0,
            'analysis_time': 0.0,
            'methods_analyzed': []
        }
        
        # RAG增强的AI审查器
        self.rag_ai_reviewer = RAGEnhancedAIReviewer(
            deepseek_api_key=deepseek_api_key,
            embedding_api_key=embedding_api_key,
            knowledge_base_path=knowledge_base_path,
            model_type=model_type  # 传递模型类型
            
        )
    
    def switch_model(self, model_type: str):
        """切换AI模型"""
        return self.rag_ai_reviewer.switch_model(model_type)
    
    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        return list_supported_models()
    
    def get_current_model_info(self) -> Dict:
        """获取当前模型信息"""
        return self.rag_ai_reviewer.response_handler.get_model_info()
    
    def get_reasoning_supported_models(self) -> List[str]:
        """获取支持推理的模型列表"""
        return REASONING_SUPPORTED_MODELS
    
    def get_detailed_error_statistics(self):
        """获取详细的错误统计信息，包含严重程度分布"""
        
        # 初始化统计 - 修复：添加 rule_severity_stats 字段
        rule_error_stats = {
            'total_rule_errors': 0,
            'high_severity': 0,
            'medium_severity': 0, 
            'low_severity': 0,
            'rule_error_details': [],
            'severity_distribution': {},
        
            'rule_severity_stats': {
                'high_severity': 0,
                'medium_severity': 0,
                'low_severity': 0,
                'has_high_severity': False
            }
        }
        
        # 统计规则错误
        if hasattr(self, 'issues') and self.issues:
            for issue in self.issues:
                severity = issue.get('severity', 'Unknown').lower()
                
                # 计入规则错误统计
                rule_error_stats['total_rule_errors'] += 1
                rule_error_stats['rule_error_details'].append({
                    'type': issue.get('type', 'Unknown'),
                    'description': issue.get('description', ''),
                    'severity': issue.get('severity', 'Unknown'),
                    'line_number': issue.get('line_number'),
                    'method_name': issue.get('method_name'),
                    'variable_name': issue.get('variable_name')
                })
                
                # 按严重程度分类（两套统计字段同时更新）
                if severity in ['high', 'critical', 'error']:
                    rule_error_stats['high_severity'] += 1
                    rule_error_stats['rule_severity_stats']['high_severity'] += 1
                    rule_error_stats['rule_severity_stats']['has_high_severity'] = True
                elif severity in ['medium', 'warning', 'warn']:
                    rule_error_stats['medium_severity'] += 1
                    rule_error_stats['rule_severity_stats']['medium_severity'] += 1
                elif severity in ['low', 'info', 'minor']:
                    rule_error_stats['low_severity'] += 1
                    rule_error_stats['rule_severity_stats']['low_severity'] += 1
                
                # 更新严重程度分布
                if severity not in rule_error_stats['severity_distribution']:
                    rule_error_stats['severity_distribution'][severity] = 0
                rule_error_stats['severity_distribution'][severity] += 1
        
        return rule_error_stats
        

    def _process_think_tags(self, content):
        """
        处理思考过程标签，将其转换为可折叠的HTML details标签
        """
        if not content:
            return content
        
        # 正则表达式匹配<think>...</think>标签及其内容
        think_pattern = r'<think>(.*?)</think>'
        
        def replace_think(match):
            think_content = match.group(1).strip()
            if not think_content:
                return ""
            
            # 将思考内容包装在可折叠的details标签中
            return f"""
<details>
<summary>💭 AI思考过程（点击展开）</summary>

```
{think_content}
```

</details>
"""
        
        # 使用正则表达式替换所有<think>标签
        processed_content = re.sub(think_pattern, replace_think, content, flags=re.DOTALL)
        
        return processed_content
    
    def load_data(self):
        """加载并解析JSON文件"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
            
            # 提取类名和类路径
            if "class_path" in self.json_data:
                self.class_path = self.json_data["class_path"]
                self.class_name = self.class_path.split('\\')[-1]
            else:
                self.class_name = os.path.basename(self.json_file_path).split('_')[0]
                
            print(f"Successfully loaded data from {self.json_file_path}")
            if self.class_path:
                print(f"Class path: {self.class_path}")
            return True
        except Exception as e:
            print(f"Error loading JSON file: {str(e)}")
            return False
    
    def set_code(self, code_str: str):
        """Set source code for analysis (normalize newlines + build line-start index)."""
        self.code_str_original = code_str  # for debugging
        # normalize newlines
        s = code_str.replace('\r\n', '\n').replace('\r', '\n')
        self.code_str = s

        # build line-start offsets for O(logN) offset->line mapping
        self._line_starts = [0]
        for i, ch in enumerate(s):
            if ch == '\n':
                self._line_starts.append(i + 1)
        return True
    


    def _line_of_offset(self, idx: int) -> int:
        """Map global character offset to 1-based line number."""
        from bisect import bisect_right
        return bisect_right(self._line_starts, idx)
    
    def add_line_numbers(self, code_str: str = None) -> str:
        s = code_str if code_str is not None else self.code_str
        if not s:
            return "No code available"
        lines = s.split('\n')
        w = len(str(len(lines)))
        return '\n'.join(f"{i+1:>{w}}: {line}" for i, line in enumerate(lines))
        
    def analyze_reference_classes(self, diagram_name='Main', method_name='calc'):
        """分析引用类"""
        if not self.class_path or not self.ascet_extractor:
            return False
                
        try:
            result = self.ascet_extractor.extract_reference_codes(
                self.class_path, diagram_name, method_name
            )
                        
            if not result:
                return False
                        
            self.reference_analysis = result
            
            # 准备引用类代码字典供AI使用
            self.reference_codes_dict = {}
            for element_name, code_info in result.get('codes', {}).items():
                if code_info.get('code'):
                    self.reference_codes_dict[element_name] = code_info
                        
            # 添加引用类相关的问题检查
            self._check_reference_class_issues(result)
                        
            return True
                    
        except Exception as e:
            print(f"引用类分析异常: {str(e)}")
            return False

    def _check_reference_class_issues(self, reference_result):
        """检查引用类相关问题"""
        codes = reference_result.get('codes', {})
                
        for element_name, code_info in codes.items():
            if code_info.get('code'):
                code = code_info['code']
                                
                if len(code) > 5000:
                    self.issues.append({
                        "type": "Reference Class Complexity",
                        "description": f"引用类 '{code_info['ref_class_name']}' 代码过长 ({len(code)} 字符)，可能存在复杂性问题",
                        "severity": "Medium",
                        "element_name": element_name,
                        "ref_class_name": code_info['ref_class_name']
                    })
                                
                if "error" in code.lower() or "exception" in code.lower():
                    self.issues.append({
                        "type": "Reference Class Error Handling",
                        "description": f"引用类 '{code_info['ref_class_name']}' 包含错误处理逻辑，需要确保错误传播正确",
                        "severity": "Low",
                        "element_name": element_name,
                        "ref_class_name": code_info['ref_class_name']
                    })
            else:
                self.issues.append({
                    "type": "Reference Class Code Extraction Failed",
                    "description": f"无法提取引用类 '{code_info['ref_class_name']}' 的代码: {code_info.get('error', '未知错误')}",
                    "severity": "Low",
                    "element_name": element_name,
                    "ref_class_name": code_info['ref_class_name']
                })
    
    def perform_basic_rule_checks(self, include_reference_analysis=True):
        """执行规则检查"""

        if self.class_path and self.ascet_extractor:
            print("预提取参数常量用于统一分析...")
            try:
                # 先提取参数映射和常量，但不重复分析
                self.extract_parameter_mappings_from_ascet(self.class_path)
                if hasattr(self, 'parameter_constants') and self.parameter_constants:
                    print(f"✓ 预提取到 {len(self.parameter_constants)} 个局部常量参数")
            except Exception as e:
                print(f"预提取参数常量失败: {e}")
                # 确保 parameter_constants 存在
                if not hasattr(self, 'parameter_constants'):
                    self.parameter_constants = []
        else:
            # 确保 parameter_constants 存在
            if not hasattr(self, 'parameter_constants'):
                self.parameter_constants = []

        # 规则检查
        self.check_unused_variables()
        self.check_used_but_unassigned_variables()
        self.check_signal_range_issues()
        self.check_complex_conditions()

        self.check_resolution_issues()

        self.check_parameter_mismatches()
        self.check_duplicate_conditions()
        self.check_infinite_loops()
        self.check_coverage_issues()
        self.check_local_return_mismatch()  # 这里集成了变量名称一致性检查
        self.check_return_statement()
        
        return self.issues
    
    # 浮点数安全比较函数
    def _safe_float_compare(self, val1_str: str, val2_str: str, rel_tol: float = 1e-3, abs_tol: float = 1e-3) -> bool:
        """
        安全的浮点数比较函数，考虑32位单精度浮点数精度问题
        
        Args:
            val1_str (str): 第一个值的字符串表示
            val2_str (str): 第二个值的字符串表示
            rel_tol (float): 相对误差容差
            abs_tol (float): 绝对误差容差
        
        Returns:
            bool: 是否相等（在容差范围内）
        """
        try:
            # 尝试转换为浮点数
            val1 = float(val1_str)
            val2 = float(val2_str)
            
            # 使用 math.isclose() 进行比较，
            return math.isclose(val1, val2, rel_tol=rel_tol, abs_tol=abs_tol)
            
        except (ValueError, TypeError):
            # 如果无法转换为浮点数，则使用字符串精确比较
            return str(val1_str) == str(val2_str)
    
    def _is_numeric_value(self, value_str: str) -> bool:
        """检查字符串是否表示数值"""
        try:
            float(value_str)
            return True
        except (ValueError, TypeError):
            return False

    def _strip_comments(self, s: str) -> str:
        """
        去除注释（// 与 /* */），同时做到：
        - 保留所有换行符（\n / \r），保证行号一致
        - 保持整体长度不变（注释内容用空格填充），保证索引不漂
        - 不清除字符串/字符常量中的 // 或 /*...*/
        """
        if not s:
            return s

        chars = list(s)
        n = len(chars)
        i = 0
        in_str = None   # None / '"' / "'"
        esc = False

        while i < n:
            ch = chars[i]

            # 处理字符串/字符常量，避免误删字符串里的注释样式
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == in_str:
                    in_str = None
                i += 1
                continue

            # 进入字符串/字符常量
            if ch == '"' or ch == "'":
                in_str = ch
                i += 1
                continue

            # 行注释 //... 到行尾（保留 \r/\n，其他替空格）
            if ch == '/' and i + 1 < n and chars[i+1] == '/':
                j = i
                # 把 '//' 两个字符也替空格
                while j < n and chars[j] not in ('\n', '\r'):
                    chars[j] = ' '
                    j += 1
                i = j  # 停在换行符上，让下一轮正常拷贝换行
                continue

            # 块注释 /* ... */（保留换行，其他替空格）
            if ch == '/' and i + 1 < n and chars[i+1] == '*':
                # 先把起始 '/*' 也替空格
                chars[i] = ' '
                chars[i+1] = ' '
                j = i + 2
                while j + 1 < n and not (chars[j] == '*' and chars[j+1] == '/'):
                    if chars[j] not in ('\n', '\r'):
                        chars[j] = ' '  # 非换行替空格
                    j += 1
                # 处理结束 '*/'
                if j < n:
                    chars[j] = ' '
                    if j + 1 < n:
                        chars[j+1] = ' '
                    i = min(j + 2, n)
                else:
                    i = n
                continue

            i += 1

        return ''.join(chars)

    def check_unused_variables(self):
        """统一检查所有类型变量和参数的使用情况（避免重复扫描）"""
        if not self.json_data:
            return False
            
        # 确保已提取所有methods的代码（包含init方法）
        if self.class_path and (not hasattr(self, 'methods_info') or not self.methods_info):
            self.extract_methods_from_ascet(include_init_for_variable_analysis=True)
        
        # 构建完整的代码文本
        complete_code = self._build_complete_code_for_analysis()
        if not complete_code:
            complete_code = self.code_str or ""
        
        # 收集所有需要检查的变量和参数
        local_vars = []
        imported_params = []
        local_constant_params = []
        
        for signal in self.json_data.get("signals", []):
            signal_name = signal.get("Name")
            if not signal_name:
                continue
                
            scope = signal.get("Scope", "")
            kind = signal.get("Kind", "")
            
            if scope == "Local" and kind == "Variable":
                local_vars.append(signal_name)
            elif scope == "Imported" and kind == "Parameter":
                imported_params.append(signal_name)
            elif scope == "Local" and kind == "Parameter":
                # 检查是否为常量参数
                if hasattr(self, 'parameter_constants') and self.parameter_constants:
                    is_constant = any(const['parameter_name'] == signal_name 
                                    for const in self.parameter_constants)
                    if is_constant:
                        local_constant_params.append(signal_name)
        
        # 统一扫描所有变量和参数的使用情况
        all_targets = local_vars + imported_params + local_constant_params
        if not all_targets:
            return True
        
        print(f"统一扫描变量使用情况: {len(local_vars)}个局部变量, {len(imported_params)}个导入参数, {len(local_constant_params)}个局部常量参数")
        
        # 使用状态机扫描代码，提取使用信息
        var_usage_info = self._scan_code_with_state_machine(complete_code, all_targets)
        
        # 存储到实例变量，供后续方法使用
        self.variable_usage_info = {
            'local_vars': {name: var_usage_info.get(name, {'assignments': 0, 'reads': 0}) 
                        for name in local_vars},
            'imported_params': {name: var_usage_info.get(name, {'assignments': 0, 'reads': 0}) 
                            for name in imported_params},
            'local_constant_params': {name: var_usage_info.get(name, {'assignments': 0, 'reads': 0}) 
                                    for name in local_constant_params}
        }
        
        # 1. 检查未使用的局部变量
        for var_name in local_vars:
            usage = self.variable_usage_info['local_vars'][var_name]
            if usage['assignments'] == 0 and usage['reads'] == 0:
                self.issues.append({
                    "type": "Local Variable Not Implemented",
                    "description": f"Variable '{var_name}' is defined but never used in any method",
                    "severity": "High"
                })
        
        # 2. 检查未使用的导入参数（存储信息，供后续映射检查使用）
        unused_imported_params = []
        for param_name in imported_params:
            usage = self.variable_usage_info['imported_params'][param_name]
            if usage['assignments'] == 0 and usage['reads'] == 0:
                unused_imported_params.append(param_name)
        
        # 存储未使用的导入参数信息
        self.unused_imported_params = set(unused_imported_params)
        print(f"发现 {len(unused_imported_params)} 个未在代码中使用的导入参数: {unused_imported_params}")
        
        # 3. 检查未使用的局部常量参数（存储信息，供后续映射检查使用）
        unused_local_constants = []
        for param_name in local_constant_params:
            usage = self.variable_usage_info['local_constant_params'][param_name]
            if usage['assignments'] == 0 and usage['reads'] == 0:
                unused_local_constants.append(param_name)
        
        # 存储未使用的局部常量参数信息
        self.unused_local_constant_params = set(unused_local_constants)
        if unused_local_constants:
            print(f"发现 {len(unused_local_constants)} 个未在代码中使用的局部常量参数: {unused_local_constants}")
                    
        return True


    def _scan_code_with_state_machine(self, code: str, target_vars: list) -> dict:
        """使用状态机扫描代码，识别变量使用情况"""
        # 初始化结果
        var_usage = {var: {'assignments': 0, 'reads': 0} for var in target_vars}
        
        # 状态枚举
        STATE_CODE = 0          # 正常代码
        STATE_LINE_COMMENT = 1  # 行注释 //
        STATE_BLOCK_COMMENT = 2 # 块注释 /* */
        STATE_STRING = 3        # 字符串 "..."
        STATE_CHAR = 4          # 字符 '...'
        
        state = STATE_CODE
        i = 0
        n = len(code)
        line_no = 1
        
        while i < n:
            char = code[i]
            
            # 更新行号
            if char == '\n':
                line_no += 1
            
            # 状态转换逻辑
            if state == STATE_CODE:
                # 正常代码状态
                if char == '/' and i + 1 < n:
                    if code[i + 1] == '/':
                        state = STATE_LINE_COMMENT
                        i += 2
                        continue
                    elif code[i + 1] == '*':
                        state = STATE_BLOCK_COMMENT
                        i += 2
                        continue
                elif char == '"':
                    state = STATE_STRING
                    i += 1
                    continue
                elif char == "'":
                    state = STATE_CHAR
                    i += 1
                    continue
                else:
                    # 在正常代码中检查变量使用
                    self._check_variable_usage_at_position(code, i, target_vars, var_usage, line_no)
            
            elif state == STATE_LINE_COMMENT:
                # 行注释状态：遇到换行符退出
                if char == '\n':
                    state = STATE_CODE
            
            elif state == STATE_BLOCK_COMMENT:
                # 块注释状态：遇到 */ 退出
                if char == '*' and i + 1 < n and code[i + 1] == '/':
                    state = STATE_CODE
                    i += 2
                    continue
            
            elif state == STATE_STRING:
                # 字符串状态：遇到非转义的 " 退出
                if char == '"' and (i == 0 or code[i-1] != '\\'):
                    state = STATE_CODE
                elif char == '\\' and i + 1 < n:
                    # 跳过转义字符
                    i += 1
            
            elif state == STATE_CHAR:
                # 字符状态：遇到非转义的 ' 退出
                if char == "'" and (i == 0 or code[i-1] != '\\'):
                    state = STATE_CODE
                elif char == '\\' and i + 1 < n:
                    # 跳过转义字符
                    i += 1
            
            i += 1
        
        return var_usage

    def _check_variable_usage_at_position(self, code: str, pos: int, target_vars: list, var_usage: dict, line_no: int):
        """在指定位置检查变量使用情况"""
        # 检查当前位置是否是标识符的开始
        if not (code[pos].isalpha() or code[pos] == '_'):
            return None
        
        # 提取标识符
        identifier = self._extract_identifier_at_position(code, pos)
        if not identifier or identifier not in target_vars:
            return None
        
        # 确认这是一个完整的标识符（词边界检查）
        if not self._is_word_boundary(code, pos, pos + len(identifier)):
            return None
        
        # 分析上下文以确定是赋值还是读取
        usage_type = self._analyze_usage_context(code, pos, len(identifier))
        
        # 更新统计
        if usage_type == 'assignment':
            var_usage[identifier]['assignments'] += 1
        elif usage_type == 'read':
            var_usage[identifier]['reads'] += 1
        
        return identifier

    def _extract_identifier_at_position(self, code: str, pos: int) -> str:
        """提取指定位置的标识符"""
        if pos >= len(code) or not (code[pos].isalpha() or code[pos] == '_'):
            return ""
        
        start = pos
        end = pos
        
        # 向后扫描
        while end < len(code) and (code[end].isalnum() or code[end] == '_'):
            end += 1
        
        return code[start:end]

    def _is_word_boundary(self, code: str, start: int, end: int) -> bool:
        """检查是否是词边界"""
        # 检查前边界
        if start > 0 and (code[start-1].isalnum() or code[start-1] == '_'):
            return False
        
        # 检查后边界
        if end < len(code) and (code[end].isalnum() or code[end] == '_'):
            return False
        
        return True

    def _analyze_usage_context(self, code: str, var_pos: int, var_len: int) -> str:
        """分析变量使用的上下文，判断是赋值还是读取"""
        var_end = var_pos + var_len
        
        # 向后看：检查是否是赋值
        next_non_space = self._find_next_non_space_char(code, var_end)
        if next_non_space != -1:
            next_char = code[next_non_space]
            
            # 检查各种赋值操作符
            if next_char == '=':
                # 检查是否是 == 或 != 等比较操作符
                if next_non_space + 1 < len(code) and code[next_non_space + 1] == '=':
                    return 'read'  # == 比较
                else:
                    return 'assignment'  # = 赋值
            elif next_char in ['+', '-', '*', '/', '%', '&', '|', '^']:
                # 检查复合赋值 +=, -=, 等
                if (next_non_space + 1 < len(code) and 
                    code[next_non_space + 1] == '='):
                    return 'assignment'
            elif next_char in ['+', '-']:
                # 检查 ++ 和 --
                if (next_non_space + 1 < len(code) and 
                    code[next_non_space + 1] == next_char):
                    return 'assignment'
        
        # 向前看：检查前缀操作符
        prev_non_space = self._find_prev_non_space_char(code, var_pos - 1)
        if prev_non_space != -1:
            prev_char = code[prev_non_space]
            
            if prev_char in ['+', '-']:
                # 检查前缀 ++ 和 --
                if (prev_non_space > 0 and 
                    code[prev_non_space - 1] == prev_char):
                    return 'assignment'
            elif prev_char == '!':
                # !variable 通常是读取
                return 'read'
        
        # 默认认为是读取使用
        return 'read'

    def _find_next_non_space_char(self, code: str, start: int) -> int:
        """查找下一个非空格字符的位置"""
        i = start
        while i < len(code) and code[i] in ' \t\n\r':
            i += 1
        return i if i < len(code) else -1

    def _find_prev_non_space_char(self, code: str, start: int) -> int:
        """查找上一个非空格字符的位置"""
        i = start
        while i >= 0 and code[i] in ' \t\n\r':
            i -= 1
        return i if i >= 0 else -1

    def _build_complete_code_for_analysis(self):
        """构建完整代码用于分析"""
        code_parts = []
        
        # 添加主方法代码
        if self.code_str:
            code_parts.append(self.code_str)
        
        # 添加所有其他methods的代码（包括init方法）
        if hasattr(self, 'methods_info') and self.methods_info:
            for method_name, method_code in self.methods_info.items():
                if method_name.lower() != 'calc' and method_code:
                    code_parts.append(method_code)
        
        return "\n".join(code_parts)
        
    def check_used_but_unassigned_variables(self):
        """
        检查被使用但从未被赋值的局部变量
        """
        if not self.json_data or not self.code_str:
            return False
            
        # 定义空白字符模式
        whitespace = r'[ \t\n\r\f\v]*'  # 零个或多个空白字符
        clean_code = self._strip_comments(self.code_str)    
        local_vars = []
        for signal in self.json_data.get("signals", []):
            if signal.get("Scope") == "Local" and signal.get("Kind") == "Variable":
                var_name = signal.get("Name")
                local_vars.append(var_name)
                    
        for var_name in local_vars:
            escaped_name = re.escape(var_name)
            
            # 赋值检测：支持各种空格情况和赋值操作符
            assignment_patterns = [
                rf'\b{escaped_name}{whitespace}={whitespace}[^=]',     # 基本赋值 var = value
                rf'\b{escaped_name}{whitespace}\+={whitespace}',       # var += value
                rf'\b{escaped_name}{whitespace}-={whitespace}',        # var -= value
                rf'\b{escaped_name}{whitespace}\*={whitespace}',       # var *= value
                rf'\b{escaped_name}{whitespace}/={whitespace}',        # var /= value
                rf'\b{escaped_name}{whitespace}%={whitespace}',        # var %= value
                rf'\b{escaped_name}{whitespace}&={whitespace}',        # var &= value
                rf'\b{escaped_name}{whitespace}\|={whitespace}',       # var |= value
                rf'\b{escaped_name}{whitespace}\^={whitespace}',       # var ^= value
                rf'\b{escaped_name}{whitespace}<<={whitespace}',       # var <<= value
                rf'\b{escaped_name}{whitespace}>>={whitespace}',       # var >>= value
                rf'\b{escaped_name}{whitespace}\+\+',                 # var++, var ++
                rf'\+\+{whitespace}{escaped_name}\b',                 # ++var, ++ var
                rf'\b{escaped_name}{whitespace}--',                   # var--, var --
                rf'--{whitespace}{escaped_name}\b',                   # --var, -- var
            ]
            
            # 检查是否有赋值
            has_assignment = any(re.search(pattern,clean_code) for pattern in assignment_patterns)
            
            # 改进的使用检测：使用词边界，精确匹配
            usage_pattern = rf'(?<![a-zA-Z0-9_]){escaped_name}(?![a-zA-Z0-9_])'
            usage_matches = list(re.finditer(usage_pattern, clean_code))
            
            # 检查是否有非赋值的使用（读取使用）
            has_read_usage = False
            for match in usage_matches:
                start, end = match.span()
                
                # 检查上下文，确定是否为读取使用
                after_var = clean_code[end:end+20]
                before_var = clean_code[max(0, start-10):start]
                
                # 如果后面不是赋值操作符，且前面不是递增递减操作符，则认为是读取使用
                is_assignment = (
                    re.match(rf'^{whitespace}=(?!=)', after_var) or        # = (不是 ==)
                    re.match(rf'^{whitespace}\+=', after_var) or           # +=
                    re.match(rf'^{whitespace}-=', after_var) or            # -=
                    re.match(rf'^{whitespace}\*=', after_var) or           # *=
                    re.match(rf'^{whitespace}/=', after_var) or            # /=
                    re.match(rf'^{whitespace}%=', after_var) or            # %=
                    re.match(rf'^{whitespace}&=', after_var) or            # &=
                    re.match(rf'^{whitespace}\|=', after_var) or           # |=
                    re.match(rf'^{whitespace}\^=', after_var) or           # ^=
                    re.match(rf'^{whitespace}<<={whitespace}', after_var) or  # <<=
                    re.match(rf'^{whitespace}>>={whitespace}', after_var) or  # >>=
                    re.match(rf'^{whitespace}\+\+', after_var) or          # ++
                    re.match(rf'^{whitespace}--', after_var) or            # --
                    re.search(rf'\+\+{whitespace}$', before_var) or        # 前缀 ++
                    re.search(rf'--{whitespace}$', before_var)             # 前缀 --
                )
                
                if not is_assignment:
                    has_read_usage = True
                    break
            
            # 如果有读取使用但没有赋值，则报告问题
            if has_read_usage and not has_assignment:
                description = f"Variable '{var_name}' is used in code but never assigned a value"
                
                self.issues.append({
                    "type": "Local Variable Not Implemented",
                    "description": description,
                    "severity": "High",
                    "variable_name": var_name
                })
                    
        return True
    
    
    

    def check_return_statement(self):
        """检查返回语句是否存在 - 检查Return Value信号是否有对应的method且包含return语句"""
        if not self.json_data:
            return False
        
        # 获取所有Return Value信号
        return_value_signals = []
        for signal in self.json_data.get("signals", []):
            if signal.get("Kind") == "Return Value":
                return_value_signals.append(signal.get("Name"))
        
        if not return_value_signals:
            return True  # 没有Return Value信号，无需检查
        
        if self.code_str:
            # 【修复】先去除注释，避免注释中的return被误报
            clean_code = self._strip_comments(self.code_str)
            
            # 查找主代码中的return语句（在去除注释后的代码中搜索）
            return_pattern = r'\breturn\s+[^;]*;'
            return_matches = re.findall(return_pattern, clean_code, re.IGNORECASE)
        
            if return_matches:
                for i, return_stmt in enumerate(return_matches, 1):
                    # 【修复】在原始代码中查找匹配位置，以获得准确的行号
                    # 因为_strip_comments保持了长度和换行符，所以可以直接查找
                    match_pos = clean_code.find(return_stmt)
                    if match_pos != -1:
                        lines_before_match = self.code_str[:match_pos].count('\n')
                        line_number = lines_before_match + 1
                        
                        # 【改进】从原始代码中提取对应位置的文本，以显示实际的代码行
                        original_line_start = self.code_str.rfind('\n', 0, match_pos) + 1
                        original_line_end = self.code_str.find('\n', match_pos)
                        if original_line_end == -1:
                            original_line_end = len(self.code_str)
                        original_line = self.code_str[original_line_start:original_line_end].strip()
                        
                        self.issues.append({
                            "type": "Invalid Return Statement in Main Code",
                            "description": f"Main code (calc method) contains return statement which is not allowed: '{original_line}' at line {line_number}",
                            "severity": "High",
                            "line_number": line_number,
                            "return_statement": original_line
                        })

        # 确保已提取methods信息
        if not hasattr(self, 'local_return_mappings') or not self.local_return_mappings:
            # 如果还没有提取，先提取methods
            if self.class_path:
                self.extract_methods_from_ascet()
                self.analyze_local_return_mappings()
        
        # 检查每个Return Value信号
        for return_signal_name in return_value_signals:
            # 检查是否有对应的method
            if return_signal_name not in self.local_return_mappings:
                self.issues.append({
                    "type": "Missing Method for Return Value",
                    "description": f"Return Value signal '{return_signal_name}' has no corresponding method implementation",
                    "severity": "High",
                    "return_signal": return_signal_name
                })
                continue
            
            # 检查method是否有return语句
            method_mappings = self.local_return_mappings[return_signal_name]
            return_statements = method_mappings.get('return_statements', [])
            
            if not return_statements:
                self.issues.append({
                    "type": "Method Missing Return Statement",
                    "description": f"Method '{return_signal_name}' exists but contains no return statement",
                    "severity": "High",
                    "method_name": return_signal_name
                })
        
        return True
    
    def check_signal_range_issues(self):
        """信号范围问题检查 - 跳过noncalibration信号"""
        if not self.json_data or not self.code_str:
            return False
        
        for signal in self.json_data.get("signals", []):
            signal_name = signal.get("Name", "")
            if signal.get("Calibration") == "noncalibration":
                continue
            if "dT" in signal_name:
                continue
                
            if "Min" in signal and "Max" in signal:
                try:
                    min_val = str(signal.get("Min"))
                    max_val = str(signal.get("Max"))
                    
                    if min_val == max_val and min_val != "---":
                        self.issues.append({
                            "type": "Signal Range Issue",
                            "description": f"Signal '{signal.get('Name')}' has identical min and max values: {min_val}",
                            "severity": "High"
                        })
                except:
                    pass
        
        return True
    
    def check_complex_conditions(self):
        """检查过于复杂的条件语句（与代码2保持一致：阈值>=10）"""
        if not self.code_str:
            return False
        
        pattern = re.compile(r'if\s*\(([^)]+)\)')
        matches = pattern.findall(self.code_str)
         
        for condition in matches:
            operator_count = condition.count('&&') + condition.count('||')
            if operator_count >= 10:  # 与代码2保持一致
                self.issues.append({
                    "type": "Too Many Conditions in IF Statement",
                    "description": f"Condition with {operator_count + 1} clauses found: '{condition}'. Recommendation is ≤10 conditions.",
                    "severity": "Medium"
                })
        
        return True
    
    


    # ==================== 精度/分辨率检查（规避注释） ====================

    def check_resolution_issues(self):
        """
        检查变量运算的潜在分辨率/精度问题

        - 扫描时直接跳过注释区域（// 与 /* */）
        """
        if not self.code_str or not self.json_data:
            return False

        vars_by_type = self._get_variables_by_type()

        # 1) sint16 三连乘溢出
        self._check_sint16_multiplication(vars_by_type.get('sint16', []))

        # 2) uint32 乘法（ASCET 溢出/位宽问题）
        self._detect_uint32_multiplication_overflow(vars_by_type.get('uint32', []))

        # 3) uint32 加法（ASCET 位移机制导致精度丢失）
        self._detect_uint32_addition_precision_loss(vars_by_type.get('uint32', []))

        # # 4) uint16 乘法溢出（基于 Impl.Max）
        # self._detect_uint16_overflow_from_json(vars_by_type.get('uint16', {}))

        # # 5) 复杂表达式累积精度丢失（PT1 白名单 + 复杂度阈值）
        # self._detect_complex_expression_precision_loss(vars_by_type)

        return True


    # ----------------- 遍历"非注释"的语句 -----------------

    def _iter_code_statements_no_comments(self, src: str):
        """
        Scan char-by-char, skipping comment contents but preserving newlines; ';' ends a statement.
        Treat '{' and '}' as hard statement boundaries (reset start), so wrapped blocks don't
        leak their start line into the next semicolon-terminated statement.
        Yields: (stmt_text, stmt_start_line, stmt_global_start)
        """
        n = len(src)
        i = 0
        line_no = 1
        in_line_comment = False
        in_block_comment = False
        in_str = None  # '"' or "'"
        esc = False

        buf = []
        stmt_start_line = 1
        stmt_has_char = False
        stmt_global_start = None  # global offset in source

        def flush_stmt():
            nonlocal buf, stmt_has_char, stmt_start_line, stmt_global_start
            out = []
            if buf and stmt_has_char:
                out_text = ''.join(buf)
                out.append((out_text, stmt_start_line, stmt_global_start))
            buf = []
            stmt_has_char = False
            stmt_global_start = None
            return out

        while i < n:
            ch = src[i]
            nxt = src[i + 1] if i + 1 < n else ''

            def bump_line(c):
                nonlocal line_no
                if c == '\n':
                    line_no += 1

            # line comment //
            if in_line_comment:
                if ch == '\n':
                    in_line_comment = False
                    buf.append('\n')  # keep newline
                bump_line(ch)
                i += 1
                continue

            # block comment /* ... */
            if in_block_comment:
                if ch == '*' and nxt == '/':
                    i += 2
                    continue
                else:
                    if ch == '\n':
                        buf.append('\n')  # keep newline
                    bump_line(ch)
                    i += 1
                    continue

            # string literal
            if in_str:
                buf.append(ch)
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == in_str:
                    in_str = None
                bump_line(ch)
                i += 1
                continue

            # enter string
            if ch == '"' or ch == "'":
                if not stmt_has_char:
                    stmt_start_line = line_no
                    stmt_global_start = i
                    stmt_has_char = True
                buf.append(ch)
                in_str = ch
                i += 1
                continue

            # enter comments?
            if ch == '/' and nxt == '/':
                in_line_comment = True
                i += 2
                continue
            if ch == '/' and nxt == '*':
                in_block_comment = True
                i += 2
                continue

            # ---------- NEW: treat braces as hard boundaries ----------
            if ch in '{}':
                # braces are not part of semicolon-terminated statements we analyze;
                # reset the current statement so the next real statement starts fresh.
                buf = []
                stmt_has_char = False
                stmt_global_start = None
                # we still append the brace if你想保留，但这里不需要
                i += 1
                continue
            # ----------------------------------------------------------

            # normal code char
            if not stmt_has_char and ch not in (' ', '\t', '\r', '\n'):
                stmt_start_line = line_no
                stmt_global_start = i
                stmt_has_char = True

            buf.append(ch)

            # statement end
            if ch == ';':
                for out in flush_stmt():
                    yield out

            bump_line(ch)
            i += 1

        # trailing buffer
        for out in flush_stmt():
            yield out



    # ----------------- 行号工具 -----------------

    def _calc_line_number_from_stmt(self, stmt_text: str, stmt_start_line: int, rel_index: int) -> int:
        """
        给定"语句文本"和该语句在原始源码中的起始行号，计算匹配点的真实行号。
        rel_index 是命中在语句内的偏移（基于 stmt_text）。
        """
        return stmt_start_line + stmt_text.count('\n', 0, rel_index)


    # ----------------- 检测项 -----------------

    def _detect_uint32_multiplication_overflow(self, uint32_vars):
        """Match only in code regions (ignore comments); line numbers refer to the original source."""
        if not self.code_str or len(uint32_vars) < 2:
            return
        import re
        var_pattern = '|'.join(re.escape(v) for v in uint32_vars)
        pat = re.compile(rf'\b({var_pattern})\b\s*\*\s*\b({var_pattern})\b')

        for stmt, start_line, stmt_g in self._iter_code_statements_no_comments(self.code_str):
            for m in pat.finditer(stmt):
                v1, v2 = m.groups()
                if v1 == v2:
                    continue
                global_idx = stmt_g + m.start()
                line_num = self._line_of_offset(global_idx)
                self.issues.append({
                    "type": "ASCET uint32 Multiplication Overflow",
                    "description": f"Line {line_num}: uint32 multiplication '{v1} * {v2}' may cause a compiler error or severe precision loss.",
                    "severity": "Medium",
                    "line_number": line_num,
                    "expression": m.group(0),
                    "ascet_behavior": "Compiler error or forced bit-shift handling"
                })


    def _detect_uint32_addition_precision_loss(self, uint32_vars):
        """Ignore comments; detect uint32 + uint32 that triggers ASCET bit-shift mechanism."""
        if not self.code_str or len(uint32_vars) < 2:
            return
        import re
        var_pattern = '|'.join(re.escape(v) for v in uint32_vars)
        pat = re.compile(rf'(?<!\+)\b({var_pattern})\b\s*\+\s*\b({var_pattern})\b(?!\+)')

        for stmt, start_line, stmt_g in self._iter_code_statements_no_comments(self.code_str):
            for m in pat.finditer(stmt):
                v1, v2 = m.groups()
                global_idx = stmt_g + m.start()
                line_num = self._line_of_offset(global_idx)
                self.issues.append({
                    "type": "ASCET uint32 Addition Bit-Shift Loss",
                    "description": f"Line {line_num}: uint32 addition '{v1} + {v2}' triggers ASCET bit-shift mechanism causing precision loss (shift-right 1 → add → shift-left 2).",
                    "severity": "Medium",
                    "line_number": line_num,
                    "expression": m.group(0),
                    "precision_loss": "Least significant bit is lost; error is amplified by post-shift"
                })


    def _detect_uint16_overflow_from_json(self, uint16_vars):
        """Match uint16 × uint16 only in code regions; line numbers refer to the original source."""
        if not uint16_vars or not self.code_str:
            return
        import re
        names = list(uint16_vars.keys())

        for stmt, start_line, stmt_g in self._iter_code_statements_no_comments(self.code_str):
            for i, a in enumerate(names):
                for b in names[i + 1:]:
                    pat = re.compile(rf'\b({re.escape(a)}\s*\*\s*{re.escape(b)}|{re.escape(b)}\s*\*\s*{re.escape(a)})\b')
                    for m in pat.finditer(stmt):
                        global_idx = stmt_g + m.start()
                        line_num = self._line_of_offset(global_idx)
                        max_result = self._calc_max_product(uint16_vars[a], uint16_vars[b])
                        if max_result and max_result > 65535:
                            ratio = max_result / 65535.0
                            self.issues.append({
                                "type": "ASCET uint16 Multiplication Overflow",
                                "description": f"Line {line_num}: uint16 multiplication '{m.group(0)}' has a maximum result ({max_result:.0f}) exceeding range by {ratio:.1f}×.",
                                "severity": self._get_overflow_severity(ratio),
                                "line_number": line_num,
                                "overflow_ratio": ratio,
                                "json_basis": f"{a}_max={uint16_vars[a]}, {b}_max={uint16_vars[b]}"
                            })


    def _detect_sint16_multiple_multiplication(self, sint16_with_max):
        """
        Match v1 * v2 * v3 within the same statement; ignore comments; line numbers map to the original source.
        """
        if not self.code_str or not sint16_with_max:
            return
        import re
        var_names = list(sint16_with_max.keys())
        if len(var_names) < 3:
            return

        for stmt, start_line, stmt_g in self._iter_code_statements_no_comments(self.code_str):
            if stmt.count('*') < 2:
                continue
            for i in range(len(var_names)):
                for j in range(i + 1, len(var_names)):
                    for k in range(j + 1, len(var_names)):
                        v1, v2, v3 = var_names[i], var_names[j], var_names[k]
                        pat = re.compile(
                            rf'(?<![A-Za-z0-9_])\(?\s*{re.escape(v1)}\s*\)?\s*\*\s*'
                            rf'\(?\s*{re.escape(v2)}\s*\)?\s*\*\s*'
                            rf'\(?\s*{re.escape(v3)}\s*\)?(?![A-Za-z0-9_])'
                        )
                        for m in pat.finditer(stmt):
                            max_result = self._calc_sint16_max_product([
                                sint16_with_max[v1], sint16_with_max[v2], sint16_with_max[v3]
                            ])
                            if max_result is None:
                                continue
                            if abs(max_result) > 32767:
                                ratio = abs(max_result) / 32767.0
                                global_idx = stmt_g + m.start()
                                line_num = self._line_of_offset(global_idx)
                                self.issues.append({
                                    "type": "ASCET sint16 Multiplication Overflow",
                                    "description": (
                                        f"Line {line_num}: three-variable sint16 multiplication '{v1}*{v2}*{v3}' "
                                        f"has a maximum magnitude ({max_result:.0f}) beyond range (-32768..32767) by {ratio:.1f}×."
                                    ),
                                    "severity": "Medium" if ratio > 2 else "low",
                                    "line_number": line_num,
                                    "expression": m.group(0),
                                    "overflow_ratio": ratio,
                                    "involved_variables": [v1, v2, v3],
                                    "source": "ASCET_method_analysis"
                                })


    def _detect_complex_expression_precision_loss(self, vars_by_type):
        """
        Cumulative precision-loss detection in complex expressions (ignore comments + PT1 whitelist + complexity threshold).
        Anchor line number to the statement's first code char (stmt_g) for exact reporting.
        """
        if not self.code_str:
            return

        sens_uint16 = set(vars_by_type.get('uint16', {}).keys())
        sens_uint32 = set(vars_by_type.get('uint32', []))
        sens_sint16 = set(vars_by_type.get('sint16', []))
        sensitive_all = sens_uint16 | sens_uint32 | sens_sint16
        if len(sensitive_all) < 2:
            return

        import re
        BIN_ARITH = re.compile(r'(?:(?:[A-Za-z0-9_\)\]])\s*)([+\-*])\s*(?:(?:[A-Za-z0-9_\(\[]))')

        def strip_calls(s: str) -> str:
            pat = re.compile(r'\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s*\([^;]*?\)')
            for _ in range(8):
                s2 = pat.sub('X', s)
                if s2 == s:
                    break
                s = s2
            return s

        # PT1 whitelist (three common forms)
        PT1_ADD_ASSIGN = re.compile(
            r'(?<!\w)([A-Za-z_]\w*)\s*\+=\s*[A-Za-z_]\w*\s*\*\s*\(\s*[A-Za-z_]\w*\s*-\s*\1\s*\)', re.ASCII)
        PT1_EQ_LHS_PLUS = re.compile(
            r'(?<!\w)([A-Za-z_]\w*)\s*=\s*\1\s*\+\s*[A-Za-z_]\w*\s*\*\s*\(\s*[A-Za-z_]\w*\s*-\s*\1\s*\)', re.ASCII)
        PT1_EQ_RHS_PLUS = re.compile(
            r'(?<!\w)([A-Za-z_]\w*)\s*=\s*[A-Za-z_]\w*\s*\*\s*\(\s*[A-Za-z_]\w*\s*-\s*\1\s*\)\s*\+\s*\1\b', re.ASCII)

        for stmt, start_line, stmt_g in self._iter_code_statements_no_comments(self.code_str):
            s = strip_calls(stmt)

            if not re.search(r'[+\-*]', s):
                continue

            # LHS filter: only when LHS is a sensitive (integer/fixed-point) type
            lhs_m_for_filter = re.match(r'^\s*([A-Za-z_]\w*)\s*(\+=|=)', s)
            if lhs_m_for_filter:
                lhs_name = lhs_m_for_filter.group(1)
                if lhs_name not in sensitive_all:
                    continue

            # PT1 whitelist
            if PT1_ADD_ASSIGN.search(s) or PT1_EQ_LHS_PLUS.search(s) or PT1_EQ_RHS_PLUS.search(s):
                continue

            ops = BIN_ARITH.findall(s)
            if len(ops) < 2:
                continue

            mul_count = ops.count('*')
            if mul_count == 0:
                continue
            if not (mul_count >= 2 or len(ops) >= 3):
                continue

            # Hit at least two sensitive variables
            sens_hit = 0
            for v in sensitive_all:
                if re.search(rf'(?<![A-Za-z0-9_]){re.escape(v)}(?![A-Za-z0-9_])', s):
                    sens_hit += 1
                    if sens_hit >= 2:
                        break
            if sens_hit < 2:
                continue

            # --- line number anchoring: use the statement's first code char ---
            line_num = self._line_of_offset(stmt_g)
            # ---------------------------------------------------------------

            preview = stmt.strip()
            if len(preview) > 120:
                preview = preview[:120] + "..."

            risk = self._assess_complex_expression_risk(len(ops), sens_hit, s, vars_by_type)
            if risk['severity'] == "Low":
                continue

            self.issues.append({
                "type": "ASCET Complex Expression Precision Loss",
                "description": f"Line {line_num}: Complex expression {risk['description']}",
                "severity": risk['severity'],
                "line_number": line_num,
                "expression": preview,
                "operator_count": len(ops),
                "risk_factors": risk['factors']
            })



    # ----------------- 其余依赖 -----------------

    def _assess_complex_expression_risk(self, op_count: int, sens_var_count: int, expr: str, vars_by_type: dict):
        """
        评估"复杂表达式累积精度丢失"的风险等级
        - op_count: 语句内二元算术运算符数量（+ - *）
        - sens_var_count: 命中的敏感变量数量（uint16/uint32/sint16 总数）
        - expr: 已折叠函数调用之后的表达式字符串
        - vars_by_type: {'uint16': {...}, 'uint32': [...], 'sint16': [...]}
        """
        factors = []
        score = 0

        # 运算符数量
        if op_count >= 4:
            score += 3
            factors.append(f"{op_count}个运算符")
        elif op_count >= 3:
            score += 2
            factors.append(f"{op_count}个运算符")
        elif op_count >= 2:
            score += 1
            factors.append(f"{op_count}个运算符")

        # 各种类型的参与度（正则词边界，避免子串误命中）
        def _count_hits(names):
            c = 0
            for v in names:
                if re.search(rf'(?<![A-Za-z0-9_]){re.escape(v)}(?![A-Za-z0-9_])', expr):
                    c += 1
            return c

        u32_hits = _count_hits(vars_by_type.get('uint32', []))
        u16_hits = _count_hits(list(vars_by_type.get('uint16', {}).keys()))
        s16_hits = _count_hits(vars_by_type.get('sint16', []))

        # uint32 参与（两个及以上加重）
        if u32_hits >= 2:
            score += 3
            factors.append(f"{u32_hits}个uint32变量")

        # uint16 乘法参与（只有含 * 才考虑）
        if '*' in expr and u16_hits >= 2:
            score += 2
            factors.append(f"{u16_hits}个uint16变量参与乘法")

        # 也可以给 sint16 一点权重（可选）
        if '*' in expr and s16_hits >= 2:
            score += 1
            factors.append(f"{s16_hits}个sint16变量参与乘法")

        # 结合总体敏感变量数量
        if sens_var_count >= 3:
            score += 1
            factors.append(f"{sens_var_count}个敏感变量命中")

        # 映射到严重度
        if score >= 5:
            sev = "Medium"
            desc = "High cumulative precision loss risk"
        elif score >= 3:
            sev = "Medium"
            desc = "High cumulative precision loss risk"
        elif score >= 1:
            sev = "Medium"
            desc = "Medium cumulative precision loss risk"
        else:
            sev = "Low"
            desc = "Low risk"

        return {"severity": sev, "description": desc, "factors": factors}


    def _get_variables_by_type(self):
        """获取按类型分组的变量信息"""
        vars_by_type = {'sint16': [], 'uint32': [], 'uint16': {}}
        for signal in self.json_data.get("signals", []):
            impl_type = signal.get("Impl. Type")
            var_name = signal.get("Name")
            if not var_name or not impl_type:
                continue
            if impl_type == "sint16":
                vars_by_type['sint16'].append(var_name)
            elif impl_type == "uint32":
                vars_by_type['uint32'].append(var_name)
            elif impl_type == "uint16":
                vars_by_type['uint16'][var_name] = signal.get("Impl. Max", "")
        return vars_by_type


    def _check_sint16_multiplication(self, sint16_vars):
        """收集 impl 范围后调用三连乘检测"""
        if not sint16_vars:
            return
        sint16_with_max = {}
        for signal in self.json_data.get("signals", []):
            if signal.get("Impl. Type") == "sint16" and signal.get("Name") in sint16_vars:
                name = signal.get("Name")
                sint16_with_max[name] = {
                    'max': signal.get("Impl. Max", ""),
                    'min': signal.get("Impl. Min", "")
                }
        if not sint16_with_max:
            return
        self._detect_sint16_multiple_multiplication(sint16_with_max)


    def _calc_sint16_max_product(self, var_infos):
        try:
            max_abs_values = []
            for var_info in var_infos:
                abs_max = self._get_sint16_abs_max(var_info)
                if abs_max is None:
                    return None
                max_abs_values.append(abs_max)
            result = 1
            for val in max_abs_values:
                result *= val
            return result
        except (ValueError, TypeError):
            return None


    def _get_sint16_abs_max(self, var_info):
        try:
            max_val = self._parse_numeric_value(var_info.get('max', ''))
            min_val = self._parse_numeric_value(var_info.get('min', ''))
            if max_val is None and min_val is None:
                return None
            abs_max = 0
            if max_val is not None:
                abs_max = max(abs_max, abs(max_val))
            if min_val is not None:
                abs_max = max(abs_max, abs(min_val))
            return abs_max if abs_max > 0 else None
        except (ValueError, TypeError):
            return None


    def _parse_numeric_value(self, val):
        if not val or val == "---":
            return None
        s = str(val).strip()
        if s.lower() in ["inf", "∞"]:
            return float('inf')
        m = re.search(r'-?[\d.]+', s)
        return float(m.group()) if m else None


    def _get_overflow_severity(self, ratio):
        if ratio > 10:
            return "High"
        elif ratio > 2:
            return "Medium"
        else:
            return "low"


    def check_parameter_mismatches(self):
        """检查本地参数和导入参数之间的不匹配"""
        if not self.json_data:
            return False
    
        if self.class_path:
            if self.extract_parameter_mappings_from_ascet(self.class_path):
                pass
        
        imported_params = {}
        local_params = {}
        
        for signal in self.json_data.get("signals", []):
            if signal.get("Scope") == "Imported" and signal.get("Kind") == "Parameter":
                imported_params[signal.get("Name")] = {
                    "min": signal.get("Min", ""),
                    "max": signal.get("Max", ""),
                    "formula": signal.get("Formula", ""),
                    "calibration": signal.get("Calibration", "")
                }
            elif signal.get("Scope") == "Local" and signal.get("Kind") == "Parameter":
                local_params[signal.get("Name")] = {
                    "min": signal.get("Min", ""),
                    "max": signal.get("Max", ""),
                    "formula": signal.get("Formula", "")
                }
        
        if self.parameter_mappings:
            self._analyze_xml_parameter_mappings(local_params, imported_params)
        
        return True
    
    def check_duplicate_conditions(self):
        """检查if语句中的重复条件"""
        if not self.code_str:
            return False
        pattern = re.compile(r'if\s*\(([^)]+)\)')
        conditions = pattern.findall(self.code_str)
        
        for condition in conditions:
            sub_conditions = []
            for op in ['&&', '||']:
                if op in condition:
                    parts = condition.split(op)
                    sub_conditions.extend([part.strip() for part in parts])
            
            if not sub_conditions:
                sub_conditions = [condition.strip()]
            
            seen = set()
            duplicates = set()
            for sub in sub_conditions:
                if sub in seen:
                    duplicates.add(sub)
                seen.add(sub)
            
            if duplicates:
                self.issues.append({
                    "type": "Duplicate Condition",
                    "description": f"Found duplicate sub-conditions in if statement: {', '.join(duplicates)}",
                    "severity": "High"
                })
        
        return True
    
    def check_infinite_loops(self):
        """检查潜在的无限循环"""
        if not self.code_str:
            return False
        
        for_pattern = re.compile(r'for\s*\([^;]*;[^;]*;[^)]*\)\s*\{')
        while_pattern = re.compile(r'while\s*\([^)]*\)\s*\{')
        
        for_loops = for_pattern.findall(self.code_str)
        while_loops = while_pattern.findall(self.code_str)
        
        for loop in while_loops:
            condition_match = re.search(r'while\s*\(([^)]*)\)', loop)
            if condition_match:
                condition = condition_match.group(1).strip()
                if condition == "true" or condition == "1":
                    self.issues.append({
                        "type": "Potential Infinite Loop",
                        "description": f"Found while loop with constant true condition: '{loop}'",
                        "severity": "High"
                    })
        
        for loop in for_loops:
            increment_match = re.search(r'for\s*\([^;]*;[^;]*;([^)]*)\)', loop)
            if increment_match:
                increment = increment_match.group(1).strip()
                if not increment:
                    self.issues.append({
                        "type": "Potential Infinite Loop",
                        "description": f"Found for loop without increment section: '{loop}'",
                        "severity": "High"
                    })
        
        return True
    
    def check_coverage_issues(self):
        """检查代码中的覆盖率问题"""
        if not self.code_str:
            return False
        
        return True
    
    def check_local_return_mismatch(self):
        """局部变量与返回值不匹配检查"""
        if not self.json_data:
            return False
    
        # 步骤1: 从ASCET提取methods
        if self.class_path:
            if self.extract_methods_from_ascet():
                self.analyze_local_return_mappings()
        
        # 步骤2: 收集变量信息
        return_values = {}
        local_variables = {}
        
        for signal in self.json_data.get("signals", []):
            signal_name = signal.get("Name")
            if not signal_name:
                continue
            
            signal_attrs = {
                "min": signal.get("Min", ""),
                "max": signal.get("Max", ""),
                "formula": signal.get("Formula", ""),
                "impl_min": signal.get("Impl. Min", ""),
                "impl_max": signal.get("Impl. Max", ""),
            }
            
            if signal.get("Kind") == "Return Value":
                return_values[signal_name] = signal_attrs
            elif signal.get("Scope") == "Local" and signal.get("Kind") == "Variable":
                local_variables[signal_name] = signal_attrs
        
        # 步骤3: 原有的属性匹配检查
        if self.local_return_mappings:
            for method_name, mappings in self.local_return_mappings.items():
                self._check_method_mappings(method_name, mappings, return_values, local_variables)
        
        # 步骤4: 更新变量名称一致性统计信息（为主AI分析准备）
        if self.local_return_mappings:
            self.name_consistency_statistics['total_method_checks'] = len(self.local_return_mappings)
            self.name_consistency_statistics['methods_analyzed'] = list(self.local_return_mappings.keys())
            self.name_consistency_statistics['ai_analysis_performed'] = True
            print(f"📋 提取到 {len(self.local_return_mappings)} 个Methods，将集成到主AI分析中")
        
        return True

    def extract_methods_from_ascet(self, diagram_name='Main', include_init_for_variable_analysis=False):
        """
        从ASCET提取指定diagram中的所有methods
        
        Args:
            diagram_name (str): 图表名称，默认为'Main'
            include_init_for_variable_analysis (bool): 是否包含init方法用于变量分析，默认False
        
        Returns:
            bool: 成功返回True，失败返回False
        """
        if not self.class_path:
            return False
            
        if not self.ascet_extractor:
            self.ascet_extractor = AscetCodeExtractor(version=self.ascet_version)
            if not self.ascet_extractor.connect():
                return False
        
        try:
            # 根据参数决定使用哪个接口
            if include_init_for_variable_analysis and hasattr(self.ascet_extractor, 'get_all_methods_for_variable_analysis'):
                # 特殊请求：使用新接口获取所有methods（包括init方法）
                self.methods_info = self.ascet_extractor.get_all_methods_for_variable_analysis(
                    self.class_path, diagram_name
                )
                return len(self.methods_info) > 0
                
            else:
                # 默认行为：使用稳定的旧接口（保持原有逻辑）
                methods_info, error = self.ascet_extractor.get_all_methods_in_diagram(
                    self.class_path, diagram_name
                )
                if error:
                    return False
                
                # 初始化methods_info字典
                self.methods_info = {}
                
                # 处理返回的methods列表
                for method in methods_info:
                    if 'error' not in method and method['code'] is not None:
                        self.methods_info[method['name']] = method['code']
                
                return True
                
        except Exception as e:
            return False

    def analyze_local_return_mappings(self):
        """分析methods中的Local和Return变量映射关系"""
        self.local_return_mappings = {}
        
        for method_name, method_code in self.methods_info.items():
            if method_name.lower() in ['calc', 'init']:
                continue
            
            mappings = self._extract_variable_mappings(method_name, method_code)
            if mappings:
                self.local_return_mappings[method_name] = mappings
        
        return self.local_return_mappings
    
    def _extract_variable_mappings(self, method_name, method_code):
        """从单个method代码中提取变量映射关系"""
        mappings = {
            'return_statements': [],
            'assignments': [],
            'method_name': method_name
        }
        
        if not method_code:
            return mappings
        
        lines = method_code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            return_match = re.search(r'return\s+([^;]+);', line)
            if return_match:
                returned_var = return_match.group(1).strip()
                mappings['return_statements'].append({
                    'line': line_num,
                    'variable': returned_var,
                    'full_statement': line
                })
            
            assignment_match = re.search(r'([^=]+)=([^=]+);', line)
            if assignment_match:
                left_var = assignment_match.group(1).strip()
                right_var = assignment_match.group(2).strip()
                mappings['assignments'].append({
                    'line': line_num,
                    'left_variable': left_var,
                    'right_variable': right_var,
                    'full_statement': line
                })
        
        return mappings

    def extract_parameter_mappings_from_ascet(self, class_path):
        """从ASCET提取参数映射关系"""
        if not self.class_path:
            return False
            
        if not self.ascet_extractor:
            self.ascet_extractor = AscetCodeExtractor(version=self.ascet_version)
            if not self.ascet_extractor.connect():
                return False
        
        try:
            xml_file_path = os.path.join(self.temp_xml_dir, "exported_class.xml")
            success, error = self.ascet_extractor.export_class_to_xml(self.class_path, xml_file_path, include_references=True)
            
            if not success:
                return False
            
            amd_files = self.find_amd_files(self.temp_xml_dir, class_path)
            
            if not amd_files:
                return False
            
            all_mappings = []
            for amd_file in amd_files:
                mappings = self.extract_parameter_mappings_from_amd(amd_file)
                all_mappings.extend(mappings)
            
            self.parameter_mappings = all_mappings
            
            self.cleanup_xml_files(self.temp_xml_dir)
            
            return True
            
        except Exception as e:
            self.cleanup_xml_files(self.temp_xml_dir)
            return False

    def find_amd_files(self, xml_export_path, class_path):
        """查找所有的.data.amd文件"""
        amd_files = []
        if class_path.startswith("\\"):
            class_path = class_path[1:]
        
        path_parts = class_path.split('\\')
        class_name = path_parts[-1]
        
        if os.path.exists(xml_export_path):
            pattern = os.path.join(xml_export_path, "**", f"{class_name}.data.amd")
            amd_files = glob.glob(pattern, recursive=True)
        return amd_files
    
    def extract_parameter_mappings_from_ascet(self, class_path):
        """
        从ASCET提取参数映射关系（增加Local常量识别）
        
        原有功能：
        1. 连接ASCET并导出XML
        2. 查找和处理AMD文件
        3. 提取参数映射关系
        4. 存储到self.parameter_mappings
        5. 清理临时文件
        6. 返回成功/失败状态
        
        新增功能：
        7. 从JSON中提取Local Parameter名称
        8. 识别和存储Local常量参数
        """
        if not self.class_path:
            return False
            
        if not self.ascet_extractor:
            self.ascet_extractor = AscetCodeExtractor(version=self.ascet_version)
            if not self.ascet_extractor.connect():
                return False
        
        try:
            # 原有功能1: 导出XML文件
            xml_file_path = os.path.join(self.temp_xml_dir, "exported_class.xml")
            success, error = self.ascet_extractor.export_class_to_xml(self.class_path, xml_file_path, include_references=True)
            
            if not success:
                return False
            
            # 原有功能2: 查找AMD文件
            amd_files = self.find_amd_files(self.temp_xml_dir, class_path)
            
            if not amd_files:
                return False
            
            # 新增功能: 从JSON中提取Local Parameter名称集合（可选，不影响原有功能）
            local_params_set = None
            if hasattr(self, 'json_data') and self.json_data and "signals" in self.json_data:
                local_params_set = set()
                for signal in self.json_data["signals"]:
                    scope = signal.get("Scope", "")
                    kind = signal.get("Kind", "")
                    name = signal.get("Name", "")
                    
                    if scope == "Local" and kind == "Parameter" and name:
                        local_params_set.add(name)
                
                if local_params_set:
                    print(f"📋 从JSON提取到Local Parameter: {local_params_set}")
                else:
                    local_params_set = None
            
            # 原有功能3: 初始化结果存储
            all_mappings = []
            
            # 新增功能: 初始化常量参数存储
            if not hasattr(self, 'parameter_constants'):
                self.parameter_constants = []
            
            # 原有功能4: 处理每个AMD文件
            for amd_file in amd_files:
                try:
                    # 保持向后兼容：支持带参数和不带参数两种调用方式
                    if local_params_set:
                        mappings = self.extract_parameter_mappings_from_amd(amd_file, local_params_set)
                    else:
                        mappings = self.extract_parameter_mappings_from_amd(amd_file)
                    
                    all_mappings.extend(mappings)
                    
                except Exception as e:
                    print(f"⚠️ 处理AMD文件失败 {os.path.basename(amd_file)}: {e}")
                    # 继续处理其他文件，不中断整个流程
                    continue
            
            # 原有功能5: 存储结果
            self.parameter_mappings = all_mappings
            
            # 原有功能6: 更新统计信息
            constant_count = len(self.parameter_constants) if hasattr(self, 'parameter_constants') else 0
            
            print(f"✓ 提取参数映射: {len(all_mappings)} 个")
            if constant_count > 0:
                print(f"✓ Local常量参数: {constant_count} 个")
            
            # 原有功能7: 清理临时文件
            self.cleanup_xml_files(self.temp_xml_dir)
            
            return True
            
        except Exception as e:
            print(f"❌ 提取参数映射失败: {e}")
            # 原有功能: 确保清理临时文件
            self.cleanup_xml_files(self.temp_xml_dir)
            return False
    
    def extract_parameter_mappings_from_amd(self, amd_file_path, local_params_set=None):
        """
        从AMD文件中提取参数映射关系（完全兼容版本）
        
        Args:
            amd_file_path (str): AMD文件路径
            local_params_set (set, optional): Local Parameter名称集合，用于常量识别
        
        Returns:
            list: 参数映射关系列表（保持原有格式）
        
        兼容性：
        - 不传local_params_set时，完全按原有逻辑处理
        - 传local_params_set时，增加Local常量识别功能
        """
        mappings = []
        
        try:
            with open(amd_file_path, 'rb') as f:
                binary_content = f.read()
            
            xml_markers = [b'<?xml', b'<ComponentData', b'<DataSet']
            xml_start = None
            
            for marker in xml_markers:
                pos = binary_content.find(marker)
                if pos != -1:
                    xml_start = pos
                    break
            
            if xml_start is None:
                return mappings
            
            potential_xml = binary_content[xml_start:]
            xml_text = potential_xml.decode('utf-8', errors='ignore')
            
            clean_xml = ''.join(char for char in xml_text if ord(char) >= 32 or char in '\n\r\t')
            
            try:
                root = ET.fromstring(clean_xml)
                
                for entry in root.findall('.//DataEntry'):
                    element_name = entry.get('elementName', 'N/A')
                    element_oid = entry.get('elementOID', 'N/A')
                    
                    # 新增功能：Local常量参数识别（仅在提供local_params_set时生效）
                    if local_params_set and element_name in local_params_set:
                        
                        # 查找Numeric元素
                        numeric_elements = entry.findall('.//Numeric')
                        
                        numeric_value = None
                        for numeric_elem in numeric_elements:
                            value = numeric_elem.get('value')
                            if value:  # value有值且不为空
                                numeric_value = value
                                break
                        
                        # 如果是Local常量，记录并跳过映射分析
                        if numeric_value is not None:
                            constant_info = {
                                'file': os.path.basename(amd_file_path),
                                'parameter_name': element_name,
                                'parameter_oid': element_oid,
                                'constant_value': numeric_value,
                                'type': 'local_constant',
                                'scope': 'Local'
                            }
                            
                            # 存储到实例变量（向后兼容）
                            if not hasattr(self, 'parameter_constants'):
                                self.parameter_constants = []
                            self.parameter_constants.append(constant_info)
                            
                            print(f"✓ Local常量: {element_name} = {numeric_value}")
                            continue  # 跳过映射分析
                    
                    # 原有功能：参数映射提取（完全保持原有逻辑）
                    for param in entry.findall('.//Parameter'):
                        formal_name = param.get('formalName', 'N/A')
                        value_name = param.get('valueName', 'N/A')
                        
                        if formal_name != 'N/A' and value_name != 'N/A':
                            mapping = {
                                'file': os.path.basename(amd_file_path),
                                'parameter_name': element_name,
                                'parameter_oid': element_oid,
                                'formal_name': formal_name,
                                'value_name': value_name,
                                'type': 'mapping'
                            }
                            mappings.append(mapping)
                            
            except ET.ParseError as e:
                print(f"XML解析错误 {amd_file_path}: {e}")
                
        except Exception as e:
            print(f"处理AMD文件时出错 {amd_file_path}: {e}")
        
        return mappings
        
    def cleanup_xml_files(self, xml_export_path):
        """删除所有导出的XML文件和目录"""
        try:
            if os.path.exists(xml_export_path):
                shutil.rmtree(xml_export_path)
        except Exception as e:
            pass
    
    def _should_skip_parameter_analysis(self, signal):
        """
        判断参数是否应该跳过分析
        
        Args:
            signal (dict): 信号信息字典
        
        Returns:
            bool: True表示应该跳过，False表示需要分析
        """
        signal_name = signal.get("Name", "")
        calibration = signal.get("Calibration", "")
        
        # 跳过noncalibration参数
        if calibration.lower() == "noncalibration":
            return True
        
        # 跳过dt相关参数（dT, dt, DT等）
        if "dt" in signal_name.lower() or signal_name.lower().startswith("dt"):
            return True
        
        return False

    
    def _analyze_xml_parameter_mappings(self, local_params, imported_params):
        """
        分析参数映射关系（修改版：跳过noncalibration和dT参数的属性检查）
        """
        if not self.parameter_mappings:
            return

        # Get constant parameters list
        constant_params = set()
        if hasattr(self, 'parameter_constants') and self.parameter_constants:
            for const in self.parameter_constants:
                constant_params.add(const['parameter_name'])
            print(f"Identified {len(constant_params)} constant parameters, excluded from mapping checks")

        # Reset statistics
        self.xml_mapping_statistics = {
            'total_mappings': len(self.parameter_mappings),
            'successful_validations': 0,
            'failed_validations': 0,
            'mismatched_parameters': 0,
            'unmapped_local_parameters': 0,
            'missing_imported_parameters': 0,
            'float_precision_issues_filtered': 0,
            'mapping_details': [],
            'noncalibration_imported_skipped': 0,
            'dt_parameters_skipped': 0,  # 新增：dT参数跳过统计
            'one_to_many_mappings_skipped': 0,
            'constant_parameters_excluded': len(constant_params),
            'constant_reference_mappings_detected': 0,
            'multi_dependency_locals_skipped': 0,
            'unreferenced_imported_parameters': 0,
        }

        # Build local parameter dependency dictionary
        local_dependencies = {}
        constant_reference_mappings = []

        for mapping in self.parameter_mappings:
            imported_param_name = mapping['value_name']
            local_param_name = mapping['parameter_name']

            # Check if it's a constant reference mapping
            if imported_param_name in constant_params:
                constant_reference_mappings.append({
                    'constant_param': imported_param_name,
                    'referencing_local_param': local_param_name,
                    'file': mapping['file'],
                    'formal_name': mapping['formal_name']
                })
                self.xml_mapping_statistics['constant_reference_mappings_detected'] += 1
                print(f"Detected constant reference: Local '{local_param_name}' references constant '{imported_param_name}'")
                continue

            # Build dependency relationships for local parameters
            if local_param_name not in local_dependencies:
                local_dependencies[local_param_name] = []

            local_dependencies[local_param_name].append({
                'imported_param': imported_param_name,
                'formal_name': mapping['formal_name'],
                'file': mapping['file'],
                'parameter_oid': mapping.get('parameter_oid', 'N/A')
            })

        # Identify multi-dependency local parameters
        multi_dependency_locals = set()
        for local_param, dependencies in local_dependencies.items():
            if len(dependencies) > 1:
                multi_dependency_locals.add(local_param)
                print(f"Detected multi-dependency local parameter: '{local_param}' depends on {len(dependencies)} imported parameters: {[dep['imported_param'] for dep in dependencies]}")

        found_mappings = 0

        # Process each local parameter's dependency relationships
        for local_param_name, dependencies in local_dependencies.items():
            local_param_exists = local_param_name in local_params

            # If local parameter depends on multiple imported parameters, skip attribute checking
            if len(dependencies) > 1:
                self.xml_mapping_statistics['multi_dependency_locals_skipped'] += 1

                # Record mapping details for each dependency, but mark as skipped
                for dep in dependencies:
                    imported_param_name = dep['imported_param']
                    imported_param_exists = imported_param_name in imported_params

                    mapping_detail = {
                        'imported_param': imported_param_name,
                        'local_param': local_param_name,
                        'imported_exists': imported_param_exists,
                        'local_exists': local_param_exists,
                        'validation_result': 'skipped_multi_dependency'
                    }
                    self.xml_mapping_statistics['mapping_details'].append(mapping_detail)

                    # Still check if parameters exist
                    if not imported_param_exists and local_param_exists:
                        self.issues.append({
                            "type": "Parameter Mapping Missing Imported", 
                            "description": f"Missing imported '{imported_param_name}' referenced by multi-dependency local '{local_param_name}'",
                            "severity": "Medium",
                            "imported_parameter": imported_param_name,
                            "local_parameter": local_param_name,
                            "xml_file": dep['file'],
                            "formal_name": dep['formal_name'],
                            "source": "XML_parameter_mapping_analysis",
                            "mapping_type": "multi_dependency"
                        })

                continue  # Skip attribute consistency checking

            # Normal processing for single-dependency local parameters
            dep = dependencies[0]
            imported_param_name = dep['imported_param']
            imported_param_exists = imported_param_name in imported_params

            mapping_detail = {
                'imported_param': imported_param_name,
                'local_param': local_param_name,
                'imported_exists': imported_param_exists,
                'local_exists': local_param_exists,
                'validation_result': 'pending'
            }

            if imported_param_exists and local_param_exists:
                found_mappings += 1
                imported_attrs = imported_params[imported_param_name]
                local_attrs = local_params[local_param_name]

                # 【修改】检查是否为noncalibration参数
                calib = str(imported_attrs.get('calibration', '')).lower()

                # 【修改】检查是否为dT参数
                is_dt_param = ('dt' in imported_param_name.lower() or 
                            'dt' in local_param_name.lower())

                if calib == 'noncalibration':
                    mapping_detail['validation_result'] = 'skipped_noncalibration'
                    self.xml_mapping_statistics['noncalibration_imported_skipped'] += 1
                    print(f"Skipped noncalibration parameter: {imported_param_name} -> {local_param_name}")
                elif is_dt_param:
                    mapping_detail['validation_result'] = 'skipped_dt_parameter'
                    self.xml_mapping_statistics['dt_parameters_skipped'] += 1
                    print(f"Skipped dT parameter: {imported_param_name} -> {local_param_name}")
                else:
                    # 传递calibration和dT信息给比较函数
                    mismatches = self._compare_parameter_attributes_with_tolerance(
                        imported_attrs, local_attrs, 
                        skip_attributes_check=False,  # 对于calibration参数仍进行检查
                        calibration=calib,
                        is_dt_parameter=is_dt_param
                    )

                    if mismatches['has_mismatch']:
                        mapping_detail['validation_result'] = 'failed'
                        self.xml_mapping_statistics['failed_validations'] += 1
                        self.xml_mapping_statistics['mismatched_parameters'] += 1

                        if mismatches['real_mismatches']:
                            mismatch_details = ", ".join(mismatches['real_mismatches'])
                            detailed_description = f"Imported '{imported_param_name}' vs Local '{local_param_name}': {mismatch_details}"

                            self.issues.append({
                                "type": "Local Parameter Mapping Import Parameter Mismatch",
                                "description": detailed_description,
                                "severity": "Medium",
                                "imported_parameter": imported_param_name,
                                "local_parameter": local_param_name,
                                "xml_file": dep['file'],
                                "formal_name": dep['formal_name'],
                                "parameter_oid": dep['parameter_oid'],
                                "source": "XML_parameter_mapping_analysis",
                                "mismatched_attributes": mismatches['real_mismatches'],
                                "mapping_type": "single_dependency",
                                "imported_attributes": {
                                    "min": imported_attrs.get('min', ''),
                                    "max": imported_attrs.get('max', ''),
                                    "formula": imported_attrs.get('formula', ''),
                                    "calibration": imported_attrs.get('calibration', '')
                                },
                                "local_attributes": {
                                    "min": local_attrs.get('min', ''),
                                    "max": local_attrs.get('max', ''),
                                    "formula": local_attrs.get('formula', '')
                                }
                            })

                        if mismatches['float_precision_filtered']:
                            self.xml_mapping_statistics['float_precision_issues_filtered'] += len(mismatches['float_precision_filtered'])
                            mapping_detail['float_precision_filtered'] = mismatches['float_precision_filtered']

                    else:
                        mapping_detail['validation_result'] = 'success'
                        self.xml_mapping_statistics['successful_validations'] += 1

            elif not imported_param_exists and local_param_exists:
                mapping_detail['validation_result'] = 'missing_imported'
                self.xml_mapping_statistics['missing_imported_parameters'] += 1

                self.issues.append({
                    "type": "Parameter Mapping Missing Imported", 
                    "description": f"Missing imported '{imported_param_name}' mapped to local '{local_param_name}'",
                    "severity": "Medium",
                    "imported_parameter": imported_param_name,
                    "local_parameter": local_param_name,
                    "xml_file": dep['file'],
                    "formal_name": dep['formal_name'],
                    "source": "XML_parameter_mapping_analysis",
                    "mapping_type": "single_dependency"
                })

            self.xml_mapping_statistics['mapping_details'].append(mapping_detail)

        # Check unmapped parameters
        self._check_unmapped_parameters(local_params, imported_params, local_dependencies, constant_params, constant_reference_mappings, multi_dependency_locals)

        # ========== 新增：准备AI参数名称一致性检测数据 ==========
        
        # 准备AI分析用的参数名称一致性检测数据
        mapping_pairs_for_ai = []
        
        # 1. 收集一对一的imported parameter → local parameter映射（用于名称一致性检测）
        one_to_one_count = 0
        for local_param_name, dependencies in local_dependencies.items():
            if len(dependencies) == 1:
                # 一对一映射，需要AI检测名称一致性
                dep = dependencies[0]
                imported_param_name = dep['imported_param']
                
                if imported_param_name in imported_params and local_param_name in local_params:
                    mapping_pairs_for_ai.append({
                        'type': 'imported_to_local',
                        'source_name': imported_param_name,
                        'target_name': local_param_name,
                        'source_info': imported_params[imported_param_name],
                        'target_info': local_params[local_param_name],
                        'xml_file': dep['file'],
                        'formal_name': dep['formal_name'],
                        'description': f"Imported '{imported_param_name}' → Local '{local_param_name}'"
                    })
                    one_to_one_count += 1
        
        # 2. 收集常量参数引用映射（local parameter → constant parameter，也需要检测名称一致性）  
        constant_ref_count = 0
        for const_ref in constant_reference_mappings:
            constant_param_name = const_ref['constant_param']
            referencing_local_param = const_ref['referencing_local_param']
            
            # 获取常量参数的详细信息
            constant_info = None
            if hasattr(self, 'parameter_constants'):
                for const in self.parameter_constants:
                    if const['parameter_name'] == constant_param_name:
                        constant_info = const
                        break
            
            if constant_info and referencing_local_param in local_params:
                mapping_pairs_for_ai.append({
                    'type': 'local_to_constant', 
                    'source_name': referencing_local_param,
                    'target_name': constant_param_name,
                    'source_info': local_params[referencing_local_param],
                    'target_info': {
                        'name': constant_param_name,
                        'value': constant_info['constant_value'],
                        'type': 'local_constant'
                    },
                    'xml_file': const_ref['file'],
                    'formal_name': const_ref['formal_name'],
                    'description': f"Local '{referencing_local_param}' → Constant '{constant_param_name}' (value={constant_info['constant_value']})"
                })
                constant_ref_count += 1
        
        # 3. 存储AI分析数据和统计信息
        if mapping_pairs_for_ai:
            self.parameter_mapping_pairs = mapping_pairs_for_ai
            
            # 初始化参数名称一致性统计
            self.param_name_consistency_statistics = {
                'total_mappings_for_ai': len(mapping_pairs_for_ai),
                'one_to_one_mappings': one_to_one_count,
                'constant_reference_mappings': constant_ref_count,
                'multi_dependency_skipped': self.xml_mapping_statistics.get('multi_dependency_locals_skipped', 0),
                'ai_analysis_prepared': True,
                'mapping_pairs_analyzed': mapping_pairs_for_ai
            }
            
            print(f"AI参数名称一致性检测数据已准备:")
            print(f"   - 一对一映射: {one_to_one_count} 个")
            print(f"   - 常量引用映射: {constant_ref_count} 个") 
            print(f"   - 总计待检测: {len(mapping_pairs_for_ai)} 个")
            
        else:
            print("无需要AI检测名称一致性的参数映射")
        
    def _prepare_parameter_mapping_context(self):
        """准备参数映射名称一致性检查的上下文信息（供AI分析使用）"""
        if not hasattr(self, 'parameter_mapping_pairs') or not self.parameter_mapping_pairs:
            return "## 参数映射名称一致性检查\n\n无可用的参数映射数据\n"
        
        context_parts = []
        context_parts.append(f"## 参数映射名称一致性检查")
        context_parts.append(f"从XML参数映射中提取到 {len(self.parameter_mapping_pairs)} 个需要检测的映射对：\n")
        
        # 分类显示映射对
        imported_to_local = [m for m in self.parameter_mapping_pairs if m['type'] == 'imported_to_local']
        local_to_constant = [m for m in self.parameter_mapping_pairs if m['type'] == 'local_to_constant']
        
        if imported_to_local:
            context_parts.append(f"### 一对一参数映射 ({len(imported_to_local)} 个)")
            for i, mapping in enumerate(imported_to_local, 1):
                context_parts.append(f"{i}. **{mapping['source_name']}** → **{mapping['target_name']}**")
                context_parts.append("")
        
        if local_to_constant:
            context_parts.append(f"### 常量参数引用映射 ({len(local_to_constant)} 个)")
            for i, mapping in enumerate(local_to_constant, 1):
                context_parts.append(f"{i}. **{mapping['source_name']}** → **{mapping['target_name']}**")
                context_parts.append("")
        
        return '\n'.join(context_parts)


    def _format_xml_mapping_statistics(self):
        """Format XML mapping statistics (Fixed: include multi-dependency information)"""
        stats = self.xml_mapping_statistics
        
        if stats['total_mappings'] == 0:
            return "## Imported Parameter -> Local Parameter \n\n Current Class has no imported Parameter and Local Parameter mappings\n"
        
        result = f"""## Imported Parameter -> Local Parameter Mapping Statistics

    ### Overall Statistics
    - **Total Mappings**: {stats['total_mappings']} items
    - **Successful Validations**: {stats['successful_validations']} items
    - **Failed Validations**: {stats['failed_validations']} items  
    - **Mismatched Parameters**: {stats['mismatched_parameters']} items
    - **Unmapped Local Parameters**: {stats['unmapped_local_parameters']} items (excluded constant and multi-dependency parameters)
    - **Missing Imported Parameters**: {stats['missing_imported_parameters']} items
    - **Local Constant Parameters Excluded**: {stats.get('local_constant_parameters_excluded', 0)} items
    - **Local Constant Reference Mappings**: {stats.get('local_constant_reference_mappings_detected', 0)} items
    - **Multi-Dependency Local Parameters**: {stats.get('multi_dependency_locals_skipped', 0)} items (attribute checking skipped)
    """
        
        # Display constant parameter information
        if hasattr(self, 'parameter_constants') and self.parameter_constants:
            result += "\n### Constant Parameter Details\n"
            for const in self.parameter_constants[:5]:  # Show max 5
                result += f"- **{const['parameter_name']}** = {const['constant_value']}\n"
            if len(self.parameter_constants) > 5:
                result += f"- ... (and {len(self.parameter_constants) - 5} more constant parameters)\n"
        
        # Display multi-dependency local parameter details
        multi_dependency_mappings = {}
        for detail in stats['mapping_details']:
            if detail['validation_result'] == 'skipped_multi_dependency':
                local_param = detail['local_param']
                if local_param not in multi_dependency_mappings:
                    multi_dependency_mappings[local_param] = []
                multi_dependency_mappings[local_param].append(detail['imported_param'])
        
        if multi_dependency_mappings:
            result += "\n### Multi-Dependency Local Parameter Details (Attribute Checking Skipped)\n"
            for local_param, imported_params in multi_dependency_mappings.items():
                result += f"- **{local_param}** depends on {len(imported_params)} imported parameters: {', '.join(imported_params)}\n"
        
        # Display failed mapping details with simplified format
        failed_mappings = [detail for detail in stats['mapping_details'] if detail['validation_result'] == 'failed']
        if failed_mappings:
            result += "\n### Failed Mapping Details\n"
            for i, mapping in enumerate(failed_mappings[:5], 1):
                result += f"{i}. **{mapping['imported_param']}** → **{mapping['local_param']}**: {mapping['validation_result']}\n"
                if 'float_precision_filtered' in mapping:
                    result += f"   - Filtered precision issues: {len(mapping['float_precision_filtered'])} items\n"
        
        return result

    def _check_unmapped_parameters(self, local_params, imported_params, local_dependencies, constant_params, constant_reference_mappings, multi_dependency_locals):
        """Check unmapped parameters (Updated: 使用预扫描的变量使用信息)"""
        
        # Check 1: Unmapped local parameters 
        mapped_local_params = set(local_dependencies.keys())
        constant_referencing_params = set()
        for ref_mapping in constant_reference_mappings:
            constant_referencing_params.add(ref_mapping['referencing_local_param'])
        
        unmapped_local = set(local_params.keys()) - mapped_local_params - constant_params - constant_referencing_params
        self.xml_mapping_statistics['unmapped_local_parameters'] = len(unmapped_local)
        
        if unmapped_local:
            print(f"Found {len(unmapped_local)} truly unmapped local parameters")
            for param in unmapped_local:
                self.issues.append({
                    "type": "Parameter Mapping Missing Local",
                    "description": f"Local parameter '{param}' not found in any mapping",
                    "severity": "Low", 
                    "local_parameter": param,
                    "source": "XML_parameter_mapping_analysis"
                })
        else:
            print("All non-constant local parameters are properly mapped or referenced")
        
        # Check 2: Unreferenced imported parameters (使用预扫描的结果)
        # 构建被引用的导入参数集合（从XML映射中提取）
        xml_referenced_imported_params = set()
        for dependencies in local_dependencies.values():
            for dep in dependencies:
                xml_referenced_imported_params.add(dep['imported_param'])
        
        # 同时检查常量引用映射中引用的常量参数
        for ref_mapping in constant_reference_mappings:
            xml_referenced_imported_params.add(ref_mapping['constant_param'])
        
        # 使用预扫描的结果：获取在代码中被使用的导入参数
        code_used_imported_params = set()
        if hasattr(self, 'unused_imported_params'):
            # 所有导入参数 - 未使用的导入参数 = 在代码中使用的导入参数
            all_imported_params = set(imported_params.keys())
            code_used_imported_params = all_imported_params - self.unused_imported_params
            print(f"从预扫描结果获取: {len(code_used_imported_params)} 个导入参数在代码中被使用")
        
        # 合并XML引用和代码使用的参数
        all_referenced_imported_params = xml_referenced_imported_params | code_used_imported_params
        
        # JSON中定义的导入参数
        defined_imported_params = set(imported_params.keys())
        
        # 找出真正未被引用的导入参数
        truly_unreferenced_imported = defined_imported_params - all_referenced_imported_params
        self.xml_mapping_statistics['unreferenced_imported_parameters'] = len(truly_unreferenced_imported)
        
        if truly_unreferenced_imported:
            print(f"Found {len(truly_unreferenced_imported)} truly unreferenced imported parameters")
            for param in truly_unreferenced_imported:
                imported_attrs = imported_params[param]
                calib = str(imported_attrs.get('calibration', '')).lower()
                
                if calib == 'noncalibration':
                    severity = "low"
                    description = f"Imported parameter '{param}' is defined but not referenced in mapping or used in code"
                else:
                    severity = "Low"
                    description = f"Imported parameter '{param}' is defined but not referenced in mapping or used in code"
                
                self.issues.append({
                    "type": "Unreferenced Imported Parameter",
                    "description": description,
                    "severity": severity,
                    "imported_parameter": param,
                    "calibration": calib,
                    "source": "XML_parameter_mapping_analysis"
                })
        else:
            print("✓ All imported parameters are properly referenced or used")
        
        # Check 3: 未使用的局部常量参数
        if hasattr(self, 'unused_local_constant_params') and self.unused_local_constant_params:
            # 检查这些未使用的常量参数是否也没有被映射引用
            unreferenced_constants = self.unused_local_constant_params.copy()
            
            # 从常量引用映射中移除被引用的常量
            for ref_mapping in constant_reference_mappings:
                unreferenced_constants.discard(ref_mapping['constant_param'])
            
            if unreferenced_constants:
                print(f"Found {len(unreferenced_constants)} unused local constant parameters")
                for param in unreferenced_constants:
                    # 获取常量值用于描述
                    constant_value = "Unknown"
                    if hasattr(self, 'parameter_constants'):
                        for const in self.parameter_constants:
                            if const['parameter_name'] == param:
                                constant_value = const['constant_value']
                                break
                    
                    self.issues.append({
                        "type": "Unused Local Constant Parameter",
                        "description": f"Local constant parameter '{param}' (value={constant_value}) is neither used in code nor referenced in mappings",
                        "severity": "Low",
                        "local_parameter": param,
                        "constant_value": constant_value,
                        "source": "unified_variable_usage_analysis"
                    })
            else:
                print("All local constant parameters are used in code or referenced in mappings")
            
    
    def _compare_parameter_attributes_with_tolerance(self, param1_attrs, param2_attrs, 
                                               skip_attributes_check=False,
                                               calibration="", 
                                               is_dt_parameter=False):
        """
        比较两个参数的属性（跳过noncalibration和dT参数检查）
        
        Args:
            param1_attrs: 第一个参数的属性
            param2_attrs: 第二个参数的属性
            skip_attributes_check: 是否跳过属性检查
            calibration: calibration类型
            is_dt_parameter: 是否为dT参数
        
        Returns:
            dict: {
                'has_mismatch': bool,
                'real_mismatches': list,
                'float_precision_filtered': list
            }
        """
        result = {
            'has_mismatch': False,
            'real_mismatches': [],
            'float_precision_filtered': []
        }
        
        # 如果明确要求跳过属性检查，则直接返回
        if skip_attributes_check:
            return result
        
        # 对于noncalibration和dT参数，跳过min/max/formula检查
        if calibration.lower() == 'noncalibration' or is_dt_parameter:
            # 只检查非关键属性，跳过min/max/formula
            print(f"Skipping min/max/formula checks for {'noncalibration' if calibration.lower() == 'noncalibration' else 'dT'} parameter")
            return result
        
        min_val = str(param1_attrs.get('min', "")).lower()
        max_val = str(param1_attrs.get('max', "")).lower()
        
        # 如果包含无穷大，跳过比较
        if min_val == "inf" or max_val == "inf":
            return result

        attrs_to_check = [
            ('min', 'Min'),
            ('max', 'Max'), 
            ('formula', 'Formula'),
            ('impl_min', 'Impl. Min'),
            ('impl_max', 'Impl. Max')   
        ]
        
        for attr_key, attr_display in attrs_to_check:
            val1 = param1_attrs.get(attr_key, "")
            val2 = param2_attrs.get(attr_key, "")
            
            # 跳过空值或占位符
            if not val1 or not val2 or val1 == "---" or val2 == "---":
                continue
                
            # 处理 formula 属性 - 使用特殊的等价性比较
            if attr_key == 'formula':
                if not self._compare_formula_values(str(val1), str(val2)):
                    result['has_mismatch'] = True
                    result['real_mismatches'].append(f"{attr_display}: '{val1}' vs '{val2}'")
                # formula 处理完后直接 continue，不再进入后续的比较逻辑
                continue
            
            # 对于数值类型，使用浮点数容差比较
            if attr_key in ['min', 'max'] and self._is_numeric_value(val1) and self._is_numeric_value(val2):
                if not self._safe_float_compare(str(val1), str(val2)):
                    # 真正的不匹配
                    result['has_mismatch'] = True
                    result['real_mismatches'].append(f"{attr_display}: '{val1}' vs '{val2}'")
                else:
                    # 检查是否原本字符串不相等但在容差范围内相等（说明是精度问题）
                    if str(val1) != str(val2):
                        result['float_precision_filtered'].append(f"{attr_display}: '{val1}' vs '{val2}' (浮点精度差异，已忽略)")
            else:
                # 其他非数值、非formula类型，使用字符串精确比较
                if str(val1) != str(val2):
                    result['has_mismatch'] = True
                    result['real_mismatches'].append(f"{attr_display}: '{val1}' vs '{val2}'")
        
        return result

    def _check_method_mappings(self, method_name, mappings, return_values, local_variables):
        """检查特定method中发现的变量映射关系（新增浮点数容差支持）"""
        for return_stmt in mappings['return_statements']:
            returned_var = return_stmt['variable']
            
            if returned_var in local_variables and method_name in return_values:
                local_attrs = local_variables[returned_var]
                return_attrs = return_values[method_name]
                
                # 使用新的浮点数容差比较方法
                mismatch_result = self._compare_attributes_with_tolerance(local_attrs, return_attrs)
                
                if mismatch_result['real_mismatches']:  # 只报告真正的不匹配
                    self.issues.append({
                        "type": " Local Value vs Return Value Mismatch",
                        "description": f"Method '{method_name}' returns local variable '{returned_var}' with mismatched: {'; '.join(mismatch_result['real_mismatches'])}",
                        "severity": "Medium",
                        "method_name": method_name,
                        "local_variable": returned_var,
                        "return_variable": method_name,
                        "line_info": f"Line {return_stmt['line']}: {return_stmt['full_statement']}",
                        "source": "ASCET_method_analysis"
                    })
        
        for assignment in mappings['assignments']:
            left_var = assignment['left_variable']
            right_var = assignment['right_variable']
            
            if left_var in return_values and right_var in local_variables:
                local_attrs = local_variables[right_var]
                return_attrs = return_values[left_var]
                
                # 使用新的浮点数容差比较方法
                mismatch_result = self._compare_attributes_with_tolerance(local_attrs, return_attrs)
                
                if mismatch_result['real_mismatches']:  # 只报告真正的不匹配
                    self.issues.append({
                        "type": "Local vs Return Value Mismatch",
                        "description": f"Assignment mismatch in method '{method_name}': local variable '{right_var}' assigned to return value '{left_var}' with incompatible attributes: {'; '.join(mismatch_result['real_mismatches'])}",
                        "severity": "Medium",
                        "method_name": method_name,
                        "local_variable": right_var,
                        "return_variable": left_var,
                        "line_info": f"Line {assignment['line']}: {assignment['full_statement']}",
                        "source": "ASCET_method_analysis"
                    })

    def _compare_formula_values(self, formula1: str, formula2: str) -> bool:
        """
        比较两个formula值，处理特殊的等价关系
        
        Args:
            formula1: 第一个formula值
            formula2: 第二个formula值
        
        Returns:
            bool: 如果formula被认为是等价的则返回True，否则返回False
        """
        # 直接相等的情况
        if formula1 == formula2:
            return True
        
        # 规范化处理：去除空格并转换为小写
        f1_normalized = formula1.strip().lower()
        f2_normalized = formula2.strip().lower()
        
        # 处理 ident 和 identity 的等价关系
        ident_variants = ['ident', 'identity']
        if f1_normalized in ident_variants and f2_normalized in ident_variants:
            print(f"Formula equivalence detected: '{formula1}' ≡ '{formula2}' (ident/identity)")
            return True
        
       
        # 其他已知的等价formula模式
      
        return False


    def _compare_attributes_with_tolerance(self, local_attrs, return_attrs):
        """
        比较local和return变量的属性（修复formula处理逻辑）
        
        Returns:
            dict: {
                'has_mismatch': bool,
                'real_mismatches': list,
                'float_precision_filtered': list
            }
        """
        result = {
            'has_mismatch': False,
            'real_mismatches': [],
            'float_precision_filtered': []
        }
        
        attrs_to_check = [
            ('min', 'Min'),
            ('max', 'Max'), 
            ('formula', 'Formula'),
            ('impl_min', 'Impl. Min'),
            ('impl_max', 'Impl. Max')
        ]
        
        for attr_key, attr_display in attrs_to_check:
            local_val = local_attrs.get(attr_key, "")
            return_val = return_attrs.get(attr_key, "")
            
            # 跳过空值或占位符
            if not local_val or not return_val or local_val == "---" or return_val == "---":
                continue
            
            # 处理 formula 属性 - 使用特殊的等价性比较
            if attr_key == 'formula':
                if not self._compare_formula_values(str(local_val), str(return_val)):
                    result['has_mismatch'] = True
                    result['real_mismatches'].append(f"{attr_display}: Local='{local_val}' vs Return='{return_val}'")
                # ✅ 关键修复：formula 处理完后直接 continue，不再进入后续的比较逻辑
                continue

            # 对于数值类型，使用浮点数容差比较
            if attr_key in ['min', 'max', 'impl_min', 'impl_max'] and self._is_numeric_value(local_val) and self._is_numeric_value(return_val):
                if not self._safe_float_compare(str(local_val), str(return_val)):
                    # 真正的不匹配
                    result['has_mismatch'] = True
                    result['real_mismatches'].append(f"{attr_display}: Local='{local_val}' vs Return='{return_val}'")
                else:
                    # 检查是否原本字符串不相等但在容差范围内相等
                    if str(local_val) != str(return_val):
                        result['float_precision_filtered'].append(f"{attr_display}: Local='{local_val}' vs Return='{return_val}' (浮点精度差异，已忽略)")
            else:
                # 其他非数值、非formula类型，使用字符串精确比较
                if str(local_val) != str(return_val):
                    result['has_mismatch'] = True
                    result['real_mismatches'].append(f"{attr_display}: Local='{local_val}' vs Return='{return_val}'")
        
        return result
    
    def _calc_max_product(self, max1_str, max2_str):
        """计算两个值的最大乘积（用于溢出检测）"""
        try:
            max1_val = self._parse_numeric_value(max1_str)
            max2_val = self._parse_numeric_value(max2_str)
            
            if max1_val is None or max2_val is None:
                return None
            
            return max1_val * max2_val
        except (ValueError, TypeError, OverflowError):
            return None
    
    def generate_rag_enhanced_review(self):
        """生成RAG增强的AI代码审查"""
        # 准备数据
        code_str_with_lines = self.add_line_numbers(self.code_str)
        signals_info = self._prepare_signals_info()
        issues_str = self._prepare_issues_str()
        
        # 传递参数映射信息给AI审查器
        if hasattr(self, 'parameter_mapping_pairs') and self.parameter_mapping_pairs:
            self.rag_ai_reviewer.parameter_mapping_pairs = self.parameter_mapping_pairs
            self.rag_ai_reviewer._prepare_parameter_mapping_context = self._prepare_parameter_mapping_context

        # 调用RAGAI审查（传递local_return_mappings）
        ai_review = self.rag_ai_reviewer.call_deepseek_with_rag(
            main_code_str=code_str_with_lines,
            reference_codes_dict=self.reference_codes_dict,
            signals_info=signals_info,
            issues_str=issues_str,
            class_path=self.class_path or "",
            local_return_mappings=self.local_return_mappings  # 传递Methods信息
        )
        
        return ai_review
    
    def _prepare_signals_info(self) -> str:
        """准备信号信息"""
        signals_info = ""
        if self.json_data and "signals" in self.json_data:
            for signal in self.json_data["signals"][:10]:
                signal_name = signal.get('Name', 'Unknown')
                signals_info += f"- {signal_name} ({signal.get('Type', 'Unknown')})\n"
        return signals_info or "No signal information available"
    
    def _prepare_issues_str(self) -> str:
        """准备问题字符串"""
        issues_str = ""
        for issue in self.issues[:5]:
            issues_str += f"- {issue['type']}: {issue['description']}\n"
        return issues_str or "No issues found"
    
    def generate_review_document(self, ai_review: str):
        """生成完整的代码审查文档（新增参数映射名称一致性统计信息）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        class_name = self.class_name or "Unknown_Class"
        
        filename = f"RAG_CodeReview_{class_name}_{timestamp}.md"
        output_dir = getattr(self, 'output_dir', None) or getattr(self, 'report_output_dir', None) or 'agent_reports'
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        # 检查RAG系统状态
        rag_status = "启用" if self.rag_ai_reviewer.case_retriever.is_available() else "未启用"
        knowledge_entries = len(self.rag_ai_reviewer.case_retriever.knowledge_entries)
        
        # 获取Token统计信息
        token_summary = global_token_tracker.get_token_summary()
        
        # 新增：参数映射统计信息
        param_mapping_summary = ""
        if hasattr(self, 'param_name_consistency_statistics'):
            stats = self.param_name_consistency_statistics
            param_mapping_summary = f"- **参数映射AI检查**: {stats.get('total_mappings_for_ai', 0)} 个映射对"
        
        document_content = f"""# ESLD代码审查报告: {class_name}

    ## 执行总结
    - **分析时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    - **类路径**: {self.class_path or "未知"}
    - **RAG系统**: {rag_status}
    - **知识库条目**: {knowledge_entries} 个历史案例
    - **规则检查问题**: {len(self.issues)} 个
    {param_mapping_summary}

    ## Token使用统计
    {token_summary}

    {self._format_xml_mapping_statistics()}

    {self._format_parameter_mapping_statistics()}

    ## 规则检查结果

    {self._format_rule_issues()}

    ---

    ## AI分析结果

    {self._format_ai_analysis(ai_review)}

    ---

    *报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
    """
        
        # 写入文档
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(document_content)
        
        return {
            "status": "success",
            "message": f"RAG增强代码审查报告生成成功: {filepath}",
            "document": document_content,
            "filename": filepath,
            "rag_enabled": rag_status == "启用",
            "knowledge_base_size": knowledge_entries,
            "xml_mapping_statistics": self.xml_mapping_statistics,
            "name_consistency_statistics": self.name_consistency_statistics,
            "param_name_consistency_statistics": getattr(self, 'param_name_consistency_statistics', {}),  # 新增
            "token_statistics": {
                "total_calls": global_token_tracker.call_count,
                "total_tokens": global_token_tracker.total_tokens,
                "prompt_tokens": global_token_tracker.total_prompt_tokens,
                "completion_tokens": global_token_tracker.total_completion_tokens
            }
        }
    
    def _format_parameter_mapping_statistics(self):
        """格式化参数映射名称一致性统计信息"""
        if not hasattr(self, 'param_name_consistency_statistics'):
            return ""
        
        stats = self.param_name_consistency_statistics
        
        if stats.get('total_mappings_for_ai', 0) == 0:
            return "## 参数映射名称一致性检查\n\n当前类无参数映射需要AI检查\n"
        
        result = f"""## 参数映射名称一致性检查

    ### 统计信息
    - **AI检查的映射对**: {stats['total_mappings_for_ai']} 个
    - **一对一映射**: {stats['one_to_one_mappings']} 个
    - **常量引用映射**: {stats['constant_reference_mappings']} 个
    - **跳过多依赖映射**: {stats['multi_dependency_skipped']} 个
    - **AI分析状态**: {'已准备' if stats['ai_analysis_prepared'] else '未准备'}

    ### 检查的映射对类型
    """
        
        # 显示一对一映射示例
        imported_to_local = [m for m in stats['mapping_pairs_analyzed'] if m['type'] == 'imported_to_local']
        if imported_to_local:
            result += f"\n**一对一参数映射** ({len(imported_to_local)} 个):\n"
            for i, mapping in enumerate(imported_to_local[:3], 1):
                result += f"{i}. **{mapping['source_name']}** → **{mapping['target_name']}**\n"
            if len(imported_to_local) > 3:
                result += f"... (还有 {len(imported_to_local) - 3} 个)\n"
        
        # 显示常量引用映射示例
        local_to_constant = [m for m in stats['mapping_pairs_analyzed'] if m['type'] == 'local_to_constant']
        if local_to_constant:
            result += f"\n**常量引用映射** ({len(local_to_constant)} 个):\n"
            for i, mapping in enumerate(local_to_constant[:3], 1):
                result += f"{i}. **{mapping['source_name']}** → **{mapping['target_name']}** (值: {mapping['target_info']['value']})\n"
            if len(local_to_constant) > 3:
                result += f"... (还有 {len(local_to_constant) - 3} 个)\n"
        
        return result
    
    def _format_xml_mapping_statistics(self):
        """Format XML mapping statistics (Fixed: include multi-dependency information)"""
        stats = self.xml_mapping_statistics
        
        if stats['total_mappings'] == 0:
            return "## Imported Parameter -> Local Parameter \n\n Current Class has no imported Parameter and Local Parameter mappings\n"
        
        result = f"""## Imported Parameter -> Local Parameter Mapping Statistics

    ### Overall Statistics
    - **Total Mappings**: {stats['total_mappings']} items
    - **Successful Validations**: {stats['successful_validations']} items
    - **Failed Validations**: {stats['failed_validations']} items  
    - **Mismatched Parameters**: {stats['mismatched_parameters']} items
    - **Unmapped Local Parameters**: {stats['unmapped_local_parameters']} items (excluded constant and multi-dependency parameters)
    - **Missing Imported Parameters**: {stats['missing_imported_parameters']} items
    - **Constant Parameters Excluded**: {stats.get('constant_parameters_excluded', 0)} items
    - **Constant Reference Mappings**: {stats.get('constant_reference_mappings_detected', 0)} items
    - **Multi-Dependency Local Parameters**: {stats.get('multi_dependency_locals_skipped', 0)} items (attribute checking skipped)
    - **- **Unreferenced Imported Parameters**: {stats.get('unreferenced_imported_parameters', 0)} items  
    """
        
        # Display constant parameter information
        if hasattr(self, 'parameter_constants') and self.parameter_constants:
            result += "\n### Constant Parameter Details\n"
            for const in self.parameter_constants[:5]:  # Show max 5
                result += f"- **{const['parameter_name']}** = {const['constant_value']}\n"
            if len(self.parameter_constants) > 5:
                result += f"- ... (and {len(self.parameter_constants) - 5} more constant parameters)\n"
        
        # Display multi-dependency local parameter details
        multi_dependency_mappings = {}
        for detail in stats['mapping_details']:
            if detail['validation_result'] == 'skipped_multi_dependency':
                local_param = detail['local_param']
                if local_param not in multi_dependency_mappings:
                    multi_dependency_mappings[local_param] = []
                multi_dependency_mappings[local_param].append(detail['imported_param'])
        
        if multi_dependency_mappings:
            result += "\n### Multi-Dependency Local Parameter Details (Attribute Checking Skipped)\n"
            for local_param, imported_params in multi_dependency_mappings.items():
                result += f"- **{local_param}** depends on {len(imported_params)} imported parameters: {', '.join(imported_params)}\n"
        
        # Display failed mapping details with simplified format
        failed_mappings = [detail for detail in stats['mapping_details'] if detail['validation_result'] == 'failed']
        if failed_mappings:
            result += "\n### Failed Mapping Details\n"
            for i, mapping in enumerate(failed_mappings[:5], 1):
                result += f"{i}. **{mapping['imported_param']}** → **{mapping['local_param']}**: {mapping['validation_result']}\n"
                if 'float_precision_filtered' in mapping:
                    result += f"   - Filtered precision issues: {len(mapping['float_precision_filtered'])} items\n"
        
        return result

    def _format_rule_issues(self):
        """格式化规则检查问题"""
        if not self.issues:
            return "✅ 未发现基础规则问题"
        
        result = f"发现 {len(self.issues)} 个基础问题：\n\n"
        
        # 按类型分组显示问题
        issues_by_type = {}
        for issue in self.issues:
            issue_type = issue['type']
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)
        
        for issue_type, type_issues in issues_by_type.items():
            result += f"### {issue_type} ({len(type_issues)} 个)\n\n"
            for i, issue in enumerate(type_issues[:3], 1):  # 每种类型最多显示3个
                result += f"{i}. **{issue['severity']}**: {issue['description']}\n"
                
                # 如果是变量名称一致性问题，显示更多详情
                if issue.get('source') == 'AI_name_consistency_analysis':
                    if issue.get('method_name'):
                        result += f"   - Method: {issue['method_name']}\n"
                    if issue.get('line_number'):
                        result += f"   - Line: {issue['line_number']}\n"
                    if issue.get('return_variable'):
                        result += f"   - Return Variable: {issue['return_variable']}\n"
                    if issue.get('local_variable'):
                        result += f"   - Local Variable: {issue['local_variable']}\n"
                    if issue.get('suggestion'):
                        result += f"   - 建议: {issue['suggestion']}\n"
            
            if len(type_issues) > 3:
                result += f"   ... (还有 {len(type_issues) - 3} 个类似问题)\n"
            result += "\n"
        
        return result

    def _format_ai_analysis(self, ai_review):
        """格式化AI分析结果 - 支持思考过程折叠"""
        # 首先处理思考过程标签
        processed_ai_review = self._process_think_tags(ai_review)
        
        # 引用类特定分析
        if self.reference_codes_dict:
            formatted = f"#### 引用类上下文分析\n\n"
            formatted += f"AI分析包含了 {len(self.reference_codes_dict)} 个引用类的代码上下文：\n"
            for element_name, code_info in self.reference_codes_dict.items():
                ref_class_name = code_info.get('ref_class_name', '未知')
                code_length = code_info.get('code_length', 0)
                formatted += f"- **{element_name}**: {ref_class_name} ({code_length} 字符)\n"
            formatted += "\n"
        else:
            formatted = "#### AI分析\n\n无引用类上下文\n\n"
        
        # AI分析内容
        formatted += f"### AI分析结果\n\n{processed_ai_review}\n"
        
        return formatted


# ==================== 主要接口函数 ====================

def extract_and_review_with_rag(class_path: str, json_file_path: str, 
                                deepseek_api_key: str, embedding_api_key: str,
                                diagram_name: str = 'Main', method_name: str = 'calc',
                                knowledge_base_path: str = "esdl_knowledge_base",
                                ascet_version: str = "6.1.4",
                                model_type: str = "gpt5-mini"):  
    """
    从ASCET提取代码并进行RAG增强的代码审查（支持多模型）
    
    Args:
        class_path (str): ASCET类路径
        json_file_path (str): JSON信号定义文件路径
        deepseek_api_key (str): AI API密钥  
        embedding_api_key (str): 嵌入向量API密钥
        diagram_name (str): 图表名称
        method_name (str): 方法名称
        knowledge_base_path (str): 知识库路径
        ascet_version (str): ASCET版本
        model_type (str): 模型类型，支持的类型可通过list_supported_models()获取
    
    Returns:
        dict: 审查结果，包含使用的模型类型信息
    """
    # 验证模型类型
    if model_type not in list_supported_models():
        return {
            "status": "error", 
            "message": f"不支持的模型类型: {model_type}。支持的模型: {list_supported_models()}"
        }
    
    # 初始化Token跟踪器
    global global_token_tracker
    global_token_tracker.reset()
    print(f"🔢 Token统计系统已重置 - 使用模型: {model_type}")
    
    # 初始化ASCET提取器
    extractor = AscetCodeExtractor(version=ascet_version)
    
    if not extractor.connect():
        return {"status": "error", "message": "Failed to connect to ASCET"}
    
    try:
        # 提取代码
        code, error = extractor.extract_method_code(class_path, diagram_name, method_name)
        
        if error:
            return {"status": "error", "message": f"Error extracting code: {error}"}
        
        if not code:
            return {"status": "error", "message": "No code extracted"}
        
        # 使用指定模型初始化RAG增强审查器
        reviewer = RAGEnhancedCodeReviewer(
            json_file_path=json_file_path,
            deepseek_api_key=deepseek_api_key,
            embedding_api_key=embedding_api_key,
            knowledge_base_path=knowledge_base_path,
            ascet_extractor=extractor,
            ascet_version=ascet_version,
            model_type=model_type  # 传递模型类型
        )
        
        # 加载数据和代码
        if not reviewer.load_data():
            return {"status": "error", "message": "Failed to load JSON data"}
        
        reviewer.set_code(code)
        
        # 执行分析
        print("🔍 执行基础规则检查...")
        basic_issues = reviewer.perform_basic_rule_checks(include_reference_analysis=True)
        
        print(f"🤖 生成RAG增强AI分析 - 模型: {model_type}...")
        ai_review = reviewer.generate_rag_enhanced_review()
        
        print("📄 生成审查报告...")
        review_doc = reviewer.generate_review_document(ai_review)
        
        # 获取详细的错误统计信息
        try:
            detailed_error_stats = reviewer.get_detailed_error_statistics()
        except Exception as e:
            print(f"警告: 获取详细错误统计失败: {e}")
            detailed_error_stats = {
                'total_rule_errors': len(basic_issues),
                'high_severity': 0,
                'medium_severity': 0,
                'low_severity': 0,
                'rule_error_details': [],
                'severity_distribution': {},
                'rule_severity_stats': {
                    'high_severity': 0,
                    'medium_severity': 0,
                    'low_severity': 0,
                    'has_high_severity': False
                }
            }
        
        # 输出Token统计
        print(f"\n{global_token_tracker.get_summary()}")
        
        return {
            "status": "success",
            "model_type": model_type,  # 返回使用的模型类型
            "model_info": reviewer.get_current_model_info(),  # 详细模型信息
            "basic_issues": basic_issues,
            "ai_review": ai_review,
            "review_document": review_doc,
            "extracted_code": code,
            "class_path": class_path,
            "reference_analysis": reviewer.reference_analysis,
            "xml_mapping_statistics": reviewer.xml_mapping_statistics,
            "name_consistency_statistics": reviewer.name_consistency_statistics,
            
            # 错误统计格式与 AscetAgentv5 完全一致
            "error_statistics": {
                "rule_errors": detailed_error_stats.get('total_rule_errors', 0),
                "ai_errors": 0,  # AI错误数量，后续可根据ai_review解析
                "total_errors": detailed_error_stats.get('total_rule_errors', 0),
                "rule_error_details": detailed_error_stats.get('rule_error_details', []),
                "ai_error_details": [],  # AI错误详情，后续可根据ai_review解析
                "rule_severity_stats": detailed_error_stats.get('rule_severity_stats', {
                    "high_severity": 0,
                    "medium_severity": 0,
                    "low_severity": 0,
                    "has_high_severity": False
                })
            },
            
            # Token统计信息
            "token_statistics": {
                "total_calls": global_token_tracker.call_count,
                "total_tokens": global_token_tracker.total_tokens,
                "prompt_tokens": global_token_tracker.total_prompt_tokens,
                "completion_tokens": global_token_tracker.total_completion_tokens,
                "estimated_cost_usd": global_token_tracker.total_tokens * 0.000014
            },
            
            # 保持向后兼容的错误统计格式
            "rule_error_details": detailed_error_stats,
            
            # 按严重程度分解的统计
            "detailed_rule_breakdown": {
                'high_severity': detailed_error_stats.get('high_severity', 0),
                'medium_severity': detailed_error_stats.get('medium_severity', 0),
                'low_severity': detailed_error_stats.get('low_severity', 0),
                'severity_distribution': detailed_error_stats.get('severity_distribution', {}),
                'rule_severity_stats': detailed_error_stats.get('rule_severity_stats', {
                    "high_severity": 0,
                    "medium_severity": 0,
                    "low_severity": 0,
                    "has_high_severity": False
                })
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}
    finally:
        extractor.disconnect()

def main():
    """主函数"""
    
    print("=" * 80)
    print("ESDL嵌入式代码审查系统（集成Token统计）")
    print("=" * 80)
    
    # 配置参数
    # class_path = r"\Customer\CC_CN\Package\ECAS_ElectronicallyControlledAirSpring\private\ECAS_HC_AxleMovingJudge"
    # json_file_path = r"ASCET_Data/ECAS_HC_AxleMovingJudge_Data_20250716_102739.json"
    class_path = r"\Customer\BYD\iTAS\iTAS_MaxTimeAchieve"
    json_file_path = r"C:\ZJR\AscetTool\ASCET_Data\iTAS_MaxTimeAchieve_Data_20250825_162412.json"
    # API密钥配置
    deepseek_api_key = "sk-jwVMOs8ac7gNmnBkB57e670f6cBd49B7A126713bF451451b"  # DeepSeek API
    embedding_api_key = "sk-yAYNtyvvu1JUE8zV0f13A3DdDeC14f6aAf442a81E6C58333"  # 向量化API
    
    # 知识库路径
    knowledge_base_path = r"C:\ZJR\AscetTool\RAG\code_analysis_knowledge"
    
    try:
        start_time = time.time()
        
        # 检查知识库状态
        case_retriever = HistoricalCaseRetriever(
            knowledge_base_path=knowledge_base_path,
            embedding_api_key=embedding_api_key
        )
        
        print(f"📚 知识库状态: {'可用' if case_retriever.is_available() else '不可用'}")
        if case_retriever.is_available():
            print(f"   历史案例数量: {len(case_retriever.knowledge_entries)}")
        
        # 执行RAG增强审查
        result = extract_and_review_with_rag(
            class_path=class_path,
            json_file_path=json_file_path,
            deepseek_api_key=deepseek_api_key,
            embedding_api_key=embedding_api_key,
            knowledge_base_path=knowledge_base_path
        )
        
        total_time = time.time() - start_time
        
        if result.get('status') == 'success':
            print(f"\n" + "="*80)
            print("✅ RAG增强代码审查完成（含变量名称一致性检查）!")
            print("="*80)
            
            review_doc = result['review_document']
            xml_stats = result.get('xml_mapping_statistics', {})
            name_stats = result.get('name_consistency_statistics', {})
            token_stats = result.get('token_statistics', {})
            
            print(f"📊 分析结果:")
            print(f"   报告文件: {review_doc['filename']}")
            print(f"   基础问题: {len(result.get('basic_issues', []))} 个")
            print(f"   RAG系统: {'✅ 启用' if review_doc.get('rag_enabled') else '❌ 未启用'}")
            print(f"   知识库规模: {review_doc.get('knowledge_base_size', 0)} 个案例")
            print(f"   总耗时: {total_time:.2f} 秒")
            
            # 显示Token使用统计
            print(f"\n💰 Token使用统计:")
            print(f"   API调用次数: {token_stats.get('total_calls', 0)} 次")
            print(f"   总Token: {token_stats.get('total_tokens', 0):,}")
            print(f"   输入Token: {token_stats.get('prompt_tokens', 0):,}")
            print(f"   输出Token: {token_stats.get('completion_tokens', 0):,}")
            print(f"   估算成本: ${token_stats.get('estimated_cost_usd', 0):.4f} USD")
            
            # 显示XML映射统计
            if xml_stats.get('total_mappings', 0) > 0:
                print(f"\n📋 XML参数映射统计:")
                print(f"   映射总数: {xml_stats['total_mappings']} 个")
                print(f"   验证成功: {xml_stats['successful_validations']} 个")
                print(f"   验证失败: {xml_stats['failed_validations']} 个")
            
            # 显示变量名称一致性统计
            if name_stats.get('ai_analysis_performed'):
                print(f"\n🏷️ 变量名称一致性统计:")
                print(f"   提取方法: {name_stats['total_method_checks']} 个")
                print(f"   集成状态: 已集成到主AI分析中")
                if name_stats['methods_analyzed']:
                    print(f"   提取的方法: {', '.join(name_stats['methods_analyzed'][:3])}{'...' if len(name_stats['methods_analyzed']) > 3 else ''}")
                print(f"   检查结果: 见主AI分析报告")
            else:
                print(f"\n🏷️ 变量名称一致性统计: 未提取到ASCET Methods数据")
            
            # 显示引用类分析结果
            if 'reference_analysis' in result and result['reference_analysis']:
                ref_analysis = result['reference_analysis']
                summary = ref_analysis['summary']
                print(f"\n🔗 引用类分析结果:")
                print(f"   发现引用: {summary['total_refs']} 个")
                print(f"   成功提取: {summary['success_extractions']} 个")
                print(f"   提取失败: {summary['failed_extractions']} 个")
            
        else:
            print(f"\n❌ 审查失败: {result.get('message', '未知错误')}")
            return 1
    
    except Exception as e:
        print(f"执行异常: {str(e)}")
        traceback.print_exc()
        return 1
    
    print("\n🎉 RAG系统运行完成")
    
    # 输出最终Token统计
    print(f"\n{global_token_tracker.get_summary()}")
   
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)