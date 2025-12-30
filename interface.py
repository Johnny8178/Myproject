from abc import ABC, abstractmethod

class AnalyzerInterface(ABC):
    @abstractmethod
    def sync_data(self, symbol: str):
        """强制数据同步规范"""
        pass

    @abstractmethod
    def run_focused_logic(self, symbol: str):
        """主力波分析规范（如近3个月分析）"""
        pass

    @abstractmethod
    def run_resonance_logic(self, symbol: str):
        """价格共振分析规范（日线主力波与分时线对齐）"""
        pass
