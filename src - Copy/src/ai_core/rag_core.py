"""
core.py - 核心业务逻辑模块
包含速率限制器、嵌入向量生成器和知识库构建器
修复了数据持久化bug，确保添加条目后立即保存到磁盘
"""

import os
import json
import re
import time
import random
import hashlib
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import requests
import faiss
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# 令牌桶算法控制请求频率
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
    """嵌入向量生成器"""
    
    def __init__(self, api_key: str, 
                 api_url: str = "http://10.161.112.104:3000/v1/embeddings", 
                 model: str = "text-embedding-3-small",
                 cache_dir: str = "embedding_cache"):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.cache_dir = cache_dir
        self.rate_limiter = RateLimiter(rate=15, per=60, burst=3)  # 每分钟15个请求
        
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

    # 为兼容性添加generate_embedding别名
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """生成嵌入向量（别名方法，用于兼容性）"""
        return self.create_embedding(text)


class CodeAnalysisKnowledgeBuilder:
    """代码分析知识库构建器 - 修复版"""
    
    def __init__(self, api_key: str, knowledge_base_path: str = "code_analysis_knowledge"):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.knowledge_base_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        self.embedding_generator = EmbeddingGenerator(api_key=api_key)
        
        # 向量存储配置
        self.dimension = 1536  # text-embedding-3-small的维度
        self.index_path = self.knowledge_base_path / "faiss_index.bin"
        self.documents_path = self.knowledge_base_path / "documents.pkl"
        self.metadata_path = self.knowledge_base_path / "metadata.json"
        
        # 修复：新增JSON格式的文档存储，便于调试和兼容性
        self.documents_json_path = self.knowledge_base_path / "documents.json"
        
        # 知识库数据
        self.knowledge_entries = []
        self.index = None
        self.metadata = {"total_entries": 0, "last_updated": None, "entry_hashes": set()}
        
        # 加载现有知识库
        self._load_existing_knowledge_base()
    
    def _load_existing_knowledge_base(self):
        """加载现有的知识库 - 修复版"""
        try:
            # 修复：强制清空内存数据，避免重复加载
            self.knowledge_entries = []
            self.index = None
            self.metadata = {"total_entries": 0, "last_updated": None, "entry_hashes": set()}
            
            # 加载元数据
            if self.metadata_path.exists():
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    metadata_dict = json.load(f)
                    self.metadata.update(metadata_dict)
                    # 转换entry_hashes为set
                    if 'entry_hashes' in metadata_dict:
                        self.metadata['entry_hashes'] = set(metadata_dict['entry_hashes'])
                print(f"[SUCCESS] 加载元数据: {self.metadata['total_entries']} 个现有条目")
            
            # 修复：优先从JSON文件加载，如果不存在则从pickle文件加载
            documents_loaded = False
            
            # 尝试从JSON文件加载
            if self.documents_json_path.exists():
                try:
                    with open(self.documents_json_path, 'r', encoding='utf-8') as f:
                        self.knowledge_entries = json.load(f)
                    print(f"[SUCCESS] 从JSON加载现有知识库: {len(self.knowledge_entries)} 个条目")
                    documents_loaded = True
                except Exception as e:
                    print(f"[WARNING] JSON文件加载失败: {e}，尝试pickle文件")
            
            # 如果JSON加载失败，尝试从pickle文件加载
            if not documents_loaded and self.documents_path.exists():
                try:
                    with open(self.documents_path, "rb") as f:
                        self.knowledge_entries = pickle.load(f)
                    print(f"[SUCCESS] 从pickle加载现有知识库: {len(self.knowledge_entries)} 个条目")
                    documents_loaded = True
                    
                    # 修复：同时保存为JSON格式，便于后续使用
                    self._save_documents_to_disk()
                except Exception as e:
                    print(f"[WARNING] pickle文件加载失败: {e}")
            
            # 加载现有索引
            index_loaded = False
            if self.index_path.exists():
                try:
                    self.index = faiss.read_index(str(self.index_path))
                    print(f"[SUCCESS] 加载现有FAISS索引: {self.index.ntotal} 个向量")
                    index_loaded = True
                except Exception as e:
                    print(f"[WARNING] 加载FAISS索引失败: {e}，将重新构建索引")
                    self.index = None
            
            # 修复：数据一致性验证
            self._validate_data_consistency()
            
            # 检查知识库完整性
            if self.knowledge_entries and not index_loaded:
                print(f"[WARNING] 索引文件缺失，需要重新构建索引以启用搜索功能")
            elif self.knowledge_entries and index_loaded:
                # 验证索引和文档数量是否匹配
                index_size = self.index.ntotal if self.index else 0
                if index_size != len(self.knowledge_entries):
                    print(f"[WARNING] 索引条目数({index_size})与文档数({len(self.knowledge_entries)})不匹配，建议重新构建索引")
                else:
                    print(f"[SUCCESS] 知识库状态良好: {len(self.knowledge_entries)} 个条目，索引已就绪")
            
        except Exception as e:
            print(f"[WARNING] 加载现有知识库时出错: {e}")
            print("将创建新的知识库")
            # 重置状态
            self.knowledge_entries = []
            self.index = None
            self.metadata = {"total_entries": 0, "last_updated": None, "entry_hashes": set()}
    
    def _validate_data_consistency(self):
        """验证数据一致性 - 新增方法"""
        try:
            docs_count = len(self.knowledge_entries)
            index_count = self.index.ntotal if self.index else 0
            meta_count = self.metadata.get('total_entries', 0)
            
            # 检查文档数与索引数的一致性
            if docs_count != index_count and index_count > 0:
                print(f"[WARNING] 数据不一致: 文档数({docs_count}) != 索引数({index_count})")
            
            # 检查文档数与元数据的一致性
            if docs_count != meta_count:
                print(f"[WARNING] 元数据不一致: 文档数({docs_count}) != 元数据数({meta_count})")
                # 自动修复元数据
                self.metadata['total_entries'] = docs_count
                print(f"[FIX] 已修复元数据中的条目数量")
            
            # 检查哈希集合的一致性
            hash_count = len(self.metadata.get('entry_hashes', set()))
            if docs_count != hash_count:
                print(f"[WARNING] 哈希集合不一致: 文档数({docs_count}) != 哈希数({hash_count})")
                # 重建哈希集合
                self.metadata['entry_hashes'] = set()
                for entry in self.knowledge_entries:
                    entry_id = entry.get('id') or entry.get('metadata', {}).get('entry_hash')
                    if entry_id:
                        self.metadata['entry_hashes'].add(entry_id)
                print(f"[FIX] 已重建哈希集合，包含 {len(self.metadata['entry_hashes'])} 个哈希")
                
        except Exception as e:
            print(f"[WARNING] 数据一致性检查失败: {str(e)}")
    
    def _generate_entry_hash(self, category: str, error_type: str, code_snippet: str, 
                           error_description: str) -> str:
        """生成条目的唯一哈希标识"""
        # 使用关键信息生成哈希
        key_info = f"{category}|{error_type}|{code_snippet[:200]}|{error_description[:200]}"
        return hashlib.md5(key_info.encode('utf-8')).hexdigest()
    
    def _is_entry_exists(self, entry_hash: str) -> bool:
        """检查条目是否已存在"""
        return entry_hash in self.metadata['entry_hashes']
    
    def add_line_numbers(self, code_str):
        """为代码添加行号"""
        if not code_str:
            return "No code available"
        
        lines = code_str.split('\n')
        numbered_lines = []
        
        # 计算行号的最大宽度，用于对齐
        max_line_num = len(lines)
        line_num_width = len(str(max_line_num))
        
        for i, line in enumerate(lines, 1):
            # 格式化行号，右对齐并补齐空格
            line_number = f"{i:>{line_num_width}}"
            numbered_line = f"{line_number}: {line}"
            numbered_lines.append(numbered_line)
        
        return '\n'.join(numbered_lines)
    
    def create_knowledge_entry(self, category: str, error_type: str, code_snippet: str, 
                             error_description: str, additional_info: str = "") -> Optional[Dict[str, Any]]:
        """创建单个知识条目"""
        
        # 生成条目哈希
        entry_hash = self._generate_entry_hash(category, error_type, code_snippet, error_description)
        
        # 检查是否已存在
        if self._is_entry_exists(entry_hash):
            print(f"[WARNING] 条目已存在，跳过: {error_type}")
            return None
        
        # 添加行号到代码
        code_with_lines = self.add_line_numbers(code_snippet)
        
        # 合成完整的语义文本
        semantic_text = f"""[CATEGORY]: {category}
[ERROR_TYPE]: {error_type}
[ERROR_DESCRIPTION]: {error_description}
[CODE_WITH_LINES]:
{code_with_lines}"""
        
        if additional_info:
            semantic_text += f"\n[ADDITIONAL_INFO]: {additional_info}"
        
        # 生成嵌入向量
        print(f"[PROCESSING] 为 {error_type} 生成嵌入向量...")
        embedding = self.embedding_generator.create_embedding(semantic_text.strip())
        
        if not embedding:
            print(f"[ERROR] 生成嵌入向量失败: {error_type}")
            return None
        
        # 创建知识条目
        entry = {
            "id": entry_hash,
            "category": category,
            "error_type": error_type,
            "error_description": error_description,
            "code_snippet": code_snippet,
            "code_with_lines": code_with_lines,
            "additional_info": additional_info,
            "semantic_text": semantic_text.strip(),
            "combined_text": semantic_text.strip(),  # 修复：添加combined_text字段兼容GUI
            "embedding": embedding,
            "metadata": {
                "timestamp": time.time(),
                "entry_hash": entry_hash,
                "content_hash": entry_hash  # 修复：添加content_hash字段兼容GUI
            }
        }
        
        return entry
    
    def _create_knowledge_entry(self, entry_config: Dict[str, Any]) -> Dict[str, Any]:
        """从配置创建知识条目 - 兼容GUI接口"""
        return self.create_knowledge_entry(
            category=entry_config.get('category', 'Unknown'),
            error_type=entry_config.get('error_type', ''),
            code_snippet=entry_config.get('code_snippet', ''),
            error_description=entry_config.get('error_description', ''),
            additional_info=entry_config.get('additional_info', '')
        )
    
    def _is_duplicate_entry(self, entry: Dict[str, Any]) -> bool:
        """检查是否为重复条目 - 兼容GUI接口"""
        entry_id = entry.get('id')
        return entry_id and self._is_entry_exists(entry_id)
    
    def add_knowledge_entries(self, entries_config: List[Dict[str, str]]) -> bool:
        """批量增量添加知识条目 - 修复版"""
        print(f"[START] 开始增量处理 {len(entries_config)} 个知识条目...")
        
        new_entries = []
        skipped_count = 0
        failed_count = 0
        
        for i, config in enumerate(entries_config, 1):
            print(f"\n[PROCESSING] 处理条目 {i}/{len(entries_config)}: {config.get('error_type', 'Unknown')}")
            
            entry = self.create_knowledge_entry(
                category=config.get('category', 'Unknown'),
                error_type=config.get('error_type', ''),
                code_snippet=config.get('code_snippet', ''),
                error_description=config.get('error_description', ''),
                additional_info=config.get('additional_info', '')
            )
            
            if entry:
                new_entries.append(entry)
                # 添加到哈希集合
                self.metadata['entry_hashes'].add(entry['id'])
                print(f"[SUCCESS] 成功添加新条目")
            elif entry is None:
                skipped_count += 1
            else:
                failed_count += 1
            
            # 添加延迟避免API限制
            if i < len(entries_config):
                time.sleep(1)
        
        # 修复：添加新条目到内存
        if new_entries:
            self.knowledge_entries.extend(new_entries)
            
            # 修复：立即保存到磁盘
            print(f"[SAVE] 正在保存 {len(new_entries)} 个新条目到磁盘...")
            self._save_documents_to_disk()
            
            # 修复：更新索引（如果存在）
            if self.index is not None:
                self._update_faiss_index(new_entries)
            
            # 修复：更新并保存元数据
            self._update_and_save_metadata()
            
            print(f"[SAVE] 已成功保存 {len(new_entries)} 个条目到磁盘")
        
        print(f"\n[STATISTICS] 增量添加统计:")
        print(f"   新增条目: {len(new_entries)}")
        print(f"   跳过条目: {skipped_count}")
        print(f"   失败条目: {failed_count}")
        print(f"   总条目数: {len(self.knowledge_entries)}")
        
        return len(new_entries) > 0
    
    def _save_documents_to_disk(self):
        """保存文档到磁盘 - 新增方法"""
        try:
            # 准备保存数据（移除embedding以节省空间）
            save_data = []
            for entry in self.knowledge_entries:
                save_entry = entry.copy()
                # 移除embedding以节省磁盘空间
                save_entry.pop('embedding', None)
                save_data.append(save_entry)
            
            # 修复：同时保存为JSON和pickle格式
            # 保存JSON格式（便于调试和跨平台兼容）
            with open(self.documents_json_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            print(f"[SAVE] 已保存JSON文档: {len(save_data)} 个条目 -> {self.documents_json_path}")
            
            # 保存pickle格式（保持向后兼容）
            with open(self.documents_path, "wb") as f:
                pickle.dump(save_data, f)
            print(f"[SAVE] 已保存pickle文档: {len(save_data)} 个条目 -> {self.documents_path}")
            
        except Exception as e:
            print(f"[ERROR] 保存文档失败: {str(e)}")
            raise
    
    def _update_faiss_index(self, new_entries: List[Dict[str, Any]]):
        """更新FAISS索引 - 新增方法"""
        try:
            if not new_entries:
                return
            
            # 提取新的嵌入向量
            new_embeddings = []
            for entry in new_entries:
                if 'embedding' in entry and self._validate_embedding_for_index(entry['embedding']):
                    new_embeddings.append(entry['embedding'])
            
            if not new_embeddings:
                print("[WARNING] 没有有效的新嵌入向量需要添加到索引")
                return
            
            new_embeddings_array = np.array(new_embeddings, dtype=np.float32)
            
            # 如果没有现有索引，创建新索引
            if self.index is None:
                print("[CREATE] 创建新的FAISS索引...")
                self.index = faiss.IndexFlatL2(self.dimension)
            
            # 添加新向量到索引
            self.index.add(new_embeddings_array)
            
            # 保存更新后的索引
            self._save_index_to_disk()
            
            print(f"[UPDATE] 已将 {len(new_embeddings)} 个向量添加到索引，当前索引大小: {self.index.ntotal}")
            
        except Exception as e:
            print(f"[ERROR] 更新FAISS索引失败: {str(e)}")
            # 如果更新失败，清空索引以避免不一致
            self.index = None
            print("[FIX] 已清空索引，建议重建索引")
    
    def _save_index_to_disk(self):
        """保存索引到磁盘 - 新增方法"""
        try:
            if self.index is not None and self.index.ntotal > 0:
                faiss.write_index(self.index, str(self.index_path))
                print(f"[SAVE] 已保存FAISS索引: {self.index.ntotal} 个向量 -> {self.index_path}")
            else:
                print("[WARNING] 索引为空，跳过保存")
                
        except Exception as e:
            print(f"[ERROR] 保存索引失败: {str(e)}")
            raise
    
    def _update_and_save_metadata(self):
        """更新并保存元数据 - 新增方法"""
        try:
            # 更新元数据
            self.metadata.update({
                "total_entries": len(self.knowledge_entries),
                "last_updated": time.time(),
                "unique_hashes": len(self.metadata['entry_hashes'])
            })
            
            # 转换set为list以便JSON序列化
            metadata_to_save = self.metadata.copy()
            metadata_to_save['entry_hashes'] = list(self.metadata['entry_hashes'])
            
            # 保存元数据
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_to_save, f, indent=2, ensure_ascii=False)
            
            print(f"[SAVE] 已更新元数据: {self.metadata['total_entries']} 个条目 -> {self.metadata_path}")
            
        except Exception as e:
            print(f"[ERROR] 保存元数据失败: {str(e)}")
            raise
    
    def build_vector_index(self) -> bool:
        """构建向量索引 - 修复版"""
        if not self.knowledge_entries:
            print("[ERROR] 没有知识条目可用于构建索引")
            return False
        
        print(f"[BUILD] 构建向量索引，包含 {len(self.knowledge_entries)} 个条目...")
        
        # 分类处理条目：有embedding的和需要生成embedding的
        entries_with_embedding = []
        entries_need_embedding = []
        
        for entry in self.knowledge_entries:
            if "embedding" in entry and self._validate_embedding_for_index(entry["embedding"]):
                entries_with_embedding.append(entry)
            else:
                entries_need_embedding.append(entry)
        
        print(f"[ANALYSIS] 条目分析: {len(entries_with_embedding)} 个已有向量, {len(entries_need_embedding)} 个需要生成")
        
        # 为缺少嵌入向量的条目生成向量
        if entries_need_embedding:
            print(f"[PROCESSING] 正在为 {len(entries_need_embedding)} 个条目生成嵌入向量...")
            
            for i, entry in enumerate(entries_need_embedding):
                print(f"[EMBEDDING] 生成向量 ({i+1}/{len(entries_need_embedding)}): {entry.get('error_type', 'Unknown')}")
                
                # 构建语义文本
                semantic_text = f"""[CATEGORY]: {entry.get('category', '')}
[ERROR_TYPE]: {entry.get('error_type', '')}
[ERROR_DESCRIPTION]: {entry.get('error_description', '')}
[CODE_WITH_LINES]:
{entry.get('code_with_lines', '')}"""
                
                if entry.get('additional_info'):
                    semantic_text += f"\n[ADDITIONAL_INFO]: {entry.get('additional_info')}"
                
                # 生成嵌入向量
                embedding = self.embedding_generator.create_embedding(semantic_text.strip())
                
                if embedding and self._validate_embedding_for_index(embedding):
                    entry["embedding"] = embedding
                    entry["semantic_text"] = semantic_text.strip()
                    entry["combined_text"] = semantic_text.strip()  # 兼容性
                    entries_with_embedding.append(entry)
                    print(f"[SUCCESS] 生成成功")
                else:
                    print(f"[ERROR] 生成失败，跳过该条目")
                
                # 添加延迟避免API限制
                if i < len(entries_need_embedding) - 1:
                    time.sleep(1)
        
        # 使用所有有效条目
        valid_entries = entries_with_embedding
        
        if not valid_entries:
            print("[ERROR] 没有有效的条目可用于构建索引")
            return False
        
        print(f"[SUCCESS] 准备构建索引: {len(valid_entries)} 个有效条目")
        
        # 提取嵌入向量
        embeddings = [entry["embedding"] for entry in valid_entries]
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # 检查数组有效性
        if np.any(np.isnan(embeddings_array)) or np.any(np.isinf(embeddings_array)):
            print("[ERROR] 嵌入向量数组包含无效值")
            return False
        
        # 创建新的FAISS索引
        self.index = faiss.IndexFlatL2(self.dimension)
        
        try:
            self.index.add(embeddings_array)
            print(f"[SUCCESS] 成功添加 {embeddings_array.shape[0]} 个向量到索引")
        except Exception as e:
            print(f"[ERROR] 添加向量到索引时出错: {e}")
            return False
        
        # 修复：保存所有数据
        try:
            # 更新内存中的知识条目
            self.knowledge_entries = valid_entries
            
            # 保存索引
            self._save_index_to_disk()
            
            # 保存文档
            self._save_documents_to_disk()
            
            # 更新并保存元数据
            self._update_and_save_metadata()
            
            print(f"[COMPLETE] 索引构建完成！总计 {len(valid_entries)} 个条目")
            return True
            
        except Exception as e:
            print(f"[ERROR] 保存数据时出错: {e}")
            return False
    
    def _validate_embedding_for_index(self, embedding) -> bool:
        """验证嵌入向量是否适用于索引构建"""
        if not embedding:
            return False
        
        try:
            # 转换为numpy数组
            embedding_array = np.array(embedding, dtype=np.float32)
            
            # 检查维度
            if embedding_array.shape[0] != self.dimension:
                return False
            
            # 检查是否包含异常值
            if np.any(np.isnan(embedding_array)) or np.any(np.isinf(embedding_array)):
                return False
            
            # 检查向量范数
            norm = np.linalg.norm(embedding_array)
            if norm == 0 or norm > 100:
                return False
            
            return True
        except Exception:
            return False
    
    def search_similar(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似的知识条目"""
        if not self.index:
            print("[ERROR] 索引未加载，无法进行搜索")
            return []
        
        # 生成查询向量
        query_embedding = self.embedding_generator.create_embedding(query_text)
        if not query_embedding:
            print("[ERROR] 生成查询向量失败")
            return []
        
        # 验证查询向量
        if not self._validate_embedding_for_index(query_embedding):
            print("[ERROR] 查询向量验证失败")
            return []
        
        try:
            # 搜索
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # 限制搜索数量不超过实际条目数
            actual_k = min(top_k, len(self.knowledge_entries))
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
            print(f"[ERROR] 搜索时出错: {e}")
            return []
    
    def get_knowledge_base_status(self):
        """获取知识库状态信息"""
        status = {
            "total_entries": len(self.knowledge_entries),
            "has_index": self.index is not None,
            "index_file_exists": self.index_path.exists(),
            "documents_file_exists": self.documents_path.exists() or self.documents_json_path.exists(),
            "metadata_file_exists": self.metadata_path.exists(),
            "last_updated": self.metadata.get('last_updated'),
            "unique_hashes": len(self.metadata.get('entry_hashes', set())),
            "categories": self._get_categories_summary()
        }
        return status
    
    def _get_categories_summary(self):
        """获取分类统计"""
        categories = {}
        for entry in self.knowledge_entries:
            category = entry.get('category', 'Unknown')
            error_type = entry.get('error_type', 'Unknown')
            
            if category not in categories:
                categories[category] = {}
            
            if error_type not in categories[category]:
                categories[category][error_type] = 0
            
            categories[category][error_type] += 1
        
        return categories
    

    

    def delete_entries_by_ids(self, entry_ids: List[str]) -> int:
        """根据ID删除条目 - 默认自动重建索引"""
        if not entry_ids:
            return 0
        
        original_count = len(self.knowledge_entries)
        deleted_count = 0
        
        # 修复：使用列表推导式而不是倒序删除，避免索引问题
        remaining_entries = []
        for entry in self.knowledge_entries:
            entry_id = entry.get('id')
            if entry_id in entry_ids:
                # 从哈希集合中移除
                if entry_id in self.metadata['entry_hashes']:
                    self.metadata['entry_hashes'].remove(entry_id)
                deleted_count += 1
                print(f"[DELETE] 删除条目: {entry.get('error_type', 'Unknown')}")
            else:
                remaining_entries.append(entry)
        
        # 更新条目列表
        self.knowledge_entries = remaining_entries
        
        # 修复：如果有条目被删除，立即保存更改并自动重建索引
        if deleted_count > 0:
            print(f"[DELETE] 已删除 {deleted_count} 个条目")
            
            # 立即保存文档
            self._save_documents_to_disk()
            
            # 更新并保存元数据
            self._update_and_save_metadata()
            
            # 自动重建索引
            if self.knowledge_entries:
                print("[REBUILD] 自动重建索引中...")
                try:
                    rebuild_success = self.build_vector_index()
                    if rebuild_success:
                        print("[SUCCESS] 索引自动重建完成")
                    else:
                        print("[ERROR] 索引自动重建失败")
                        self._clear_index()
                except Exception as e:
                    print(f"[ERROR] 索引自动重建出错: {e}")
                    self._clear_index()
            else:
                # 如果没有剩余条目，清空索引
                self._clear_index()
                print("[INFO] 所有条目已删除，索引已清空")
        
        return deleted_count

    def _clear_index(self):
        """清空索引的私有方法"""
        self.index = None
        if self.index_path.exists():
            try:
                self.index_path.unlink()
                print("[FIX] 已清空索引文件")
            except Exception as e:
                print(f"[WARNING] 删除索引文件失败: {e}")