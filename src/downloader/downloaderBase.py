# doc: 定义下载类的基础操作
from abc import ABC, abstractmethod
import json
from loguru import logger
import os
from dataclasses import dataclass, asdict, field
from typing import Optional, Tuple
from pathlib import Path
from ..comm import *
from curl_cffi import requests

# 下载信息，只保留最基础的信息。只需要填写avid，其他字段用于调试，选填
@dataclass
class AVDownloadInfo:
    m3u8: str = ""
    title: str = ""
    avid: str = ""

    def __str__(self):
        return (
            f"=== 元数据详情 ===\n"
            f"番号: {self.avid or '未知'}\n"
            f"标题: {self.title or '未知'}\n"
            f"M3U8: {self.m3u8 or '无'}"
        )

    def to_json(self, file_path: str, indent: int = 2) -> bool:
        try:
            path = Path(file_path) if isinstance(file_path, str) else file_path
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with path.open('w', encoding='utf-8') as f:
                json.dump(asdict(self), f, ensure_ascii=False, indent=indent)
            return True
        except (IOError, TypeError) as e:
            logger.error(f"JSON序列化失败: {str(e)}")
            return False

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

class Downloader(ABC):
    """
    使用方式：
    1. downloadInfo生成元数据，并序列化到download_info.json
    2. downloadM3u8下载视频并转成mp4格式
    3. downloadIMG下载封面和演员头像
    4. genNFO生成nfo文件
    """
    def __init__(self, path: str, proxy = None, timeout = 15):
        """
        :path: 配置的路径，如/vol2/user/missav
        :avid: 车牌号
        """
        self.path = path
        self.proxy = proxy
        self.proxies = {
            'http': proxy,
            'https': proxy
        } if proxy else None
        self.timeout = timeout
    
    def setDomain(self, domain: str) -> bool:
        if domain:  
            self.domain = domain
            return True
        return False

    @abstractmethod
    def getDownloaderName(self) -> str:
        pass

    @abstractmethod
    def getHTML(self, avid: str) -> Optional[str]:
        '''需要实现的方法：根据avid，构造url并请求，获取html, 返回字符串'''
        pass

    @abstractmethod
    def parseHTML(self, html: str, avid: str) -> Optional[AVDownloadInfo]:
        '''
        需要实现的方法：根据html，解析出元数据，返回AVDownloadInfo
        注意：实现新的downloader，只需要获取到m3u8就行了(也可以多匹配点方便调试)，元数据统一使用MissAV
        '''
        pass
    
    def downloadInfo(self, avid: str) -> Optional[AVDownloadInfo]:
        '''将元数据download_info.json序列化到到对应位置，同时返回AVDownloadInfo'''
        # 获取html
        avid = avid.upper()
        print(os.path.join(self.path, avid))
        os.makedirs(os.path.join(self.path, avid), exist_ok=True)
        html = self.getHTML(avid)
        if not html:
            logger.error("获取html失败")
            return None
        with open(os.path.join(self.path, avid, avid+".html"), "w+", encoding='utf-8') as f:
            f.write(html)

        # 从html中解析元数据，返回MissAVInfo结构体
        info = self.parseHTML(html)
        if info is None:
            logger.error("解析元数据失败")
            return None
        
        info.avid = info.avid.upper() # 强制大写
        info.to_json(os.path.join(self.path, avid, "download_info.json"))
        logger.info("已保存到 download_info.json")

        return info

    
    def _select_best_resolution(self, url: str) -> Optional[str]:
        """
        列出所有可用分辨率，选择最优的一个
        优先级：分辨率高 > 码率高
        返回格式：1920x1080 或 None
        """
        try:
            from ..comm import preferHighResolution
            if not preferHighResolution:
                return None
            
            # 构建列出分辨率的命令
            list_cmd = f"{download_tool} -u {url} -l -H Referer:http://{self.domain}"
            logger.debug(f"Listing resolutions: {list_cmd}")
            
            # 执行命令并捕获输出
            import subprocess
            result = subprocess.run(list_cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            output = result.stdout + result.stderr
            logger.debug(f"Resolution list output:\n{output}")
            
            # 解析分辨率和码率信息
            # 典型格式：
            # 1920x1080 (1920x1080, 5000k)
            # 1280x720 (1280x720, 2500k)
            resolutions = []
            for line in output.split('\n'):
                line = line.strip()
                if 'x' in line and 'k' in line.lower():
                    try:
                        # 提取分辨率信息
                        parts = line.split()
                        if len(parts) >= 1:
                            res = parts[0]
                            # 提取宽高
                            if 'x' in res:
                                w, h = map(int, res.split('x'))
                                area = w * h
                                
                                # 提取码率（默认为0）
                                bitrate = 0
                                for part in parts:
                                    if 'k' in part.lower():
                                        try:
                                            bitrate = int(part.replace('k', '').replace('K', ''))
                                            break
                                        except:
                                            pass
                                
                                resolutions.append({
                                    'resolution': res,
                                    'area': area,
                                    'bitrate': bitrate,
                                    'width': w,
                                    'height': h
                                })
                    except Exception as e:
                        logger.debug(f"Failed to parse resolution line '{line}': {e}")
                        continue
            
            if not resolutions:
                logger.info("No resolutions found in list, using default download")
                return None
            
            # 按分辨率（面积）降序排列，同分辨率下按码率降序排列
            resolutions.sort(key=lambda x: (x['area'], x['bitrate']), reverse=True)
            
            best = resolutions[0]
            logger.info(f"Best resolution selected: {best['resolution']} ({best['width']}x{best['height']}, {best['bitrate']}k)")
            
            return best['resolution']
            
        except Exception as e:
            logger.warning(f"Failed to select best resolution: {e}")
            return None
    
    def downloadM3u8(self, url: str, avid: str) -> bool:
        """m3u8视频下载"""
        os.makedirs(os.path.dirname(os.path.join(self.path, avid)), exist_ok=True)
        try:
            # 尝试选择最优分辨率
            desired_resolution = self._select_best_resolution(url)
            
            # 构建基础命令
            base_cmd = f"{download_tool} -u {url} -o {os.path.join(self.path, avid, avid+'.ts')}"
            if desired_resolution:
                base_cmd += f" -d {desired_resolution}"
            base_cmd += f" -H Referer:http://{self.domain}"
            
            if isNeedVideoProxy and self.proxy:
                logger.info("使用代理")
                command = f"{base_cmd} -p {self.proxy}"
            else:
                logger.info("不使用代理")
                command = base_cmd
            
            logger.debug(command)
            if os.system(command) != 0:
                # 难顶。。。使用代理下载失败，尝试不用代理；不用代理下载失败，尝试使用代理
                if not isNeedVideoProxy and self.proxy:
                    logger.info("尝试使用代理")
                    command = f"{base_cmd} -p {self.proxy}"
                else:
                    logger.info("尝试不使用代理")
                    command = base_cmd
                logger.debug(f"retry {command}")
                if os.system(command) != 0:
                    return False
            
            # 转mp4
            convert = f"{ffmpeg_tool} -i {os.path.join(self.path, avid, avid+'.ts')} -c copy -f mp4 {os.path.join(self.path, avid, avid+'.mp4')}"
            logger.debug(convert)
            if os.system(convert) != 0:
                return False
            if os.system(f"rm {os.path.join(self.path, avid, avid+'.ts')}") != 0:
                return False
            return True
        except Exception as e:
            logger.error(f"Exception in downloadM3u8: {e}")
            return False
    
    def _fetch_html(self, url: str, referer: str = "") -> Optional[str]:
        logger.debug(f"fetch url: {url}")
        try:
            newHeader = headers
            if referer:
                newHeader["Referer"] = referer
            response = requests.get(
                url,
                proxies=self.proxies,
                headers=newHeader,
                timeout=self.timeout,
                impersonate="chrome110",  # 可选：chrome, chrome110, edge99, safari15_5
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
    