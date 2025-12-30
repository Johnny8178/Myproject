-- 洪都航空分析模型表结构 
-- 版本: 1.0

-- 1. 原始行情数据
CREATE TABLE IF NOT EXISTS hongdu_stock (
    trade_date    DATE PRIMARY KEY,    -- 交易日期
    close_price   DOUBLE,              -- 收盘价
    volume        DOUBLE,              -- 成交量（用于贝叶斯权重）
    high_price    DOUBLE,
    low_price     DOUBLE
);

-- 2. 正弦波分解分量
CREATE TABLE IF NOT EXISTS sine_waves (
    trade_date    DATE,
    wave_id       INTEGER,             -- 波编号 (1=主力)
    amplitude     DOUBLE,              -- 振幅
    phase_shift   DOUBLE,              -- 相位领先
    wave_value    DOUBLE,              -- 该点正弦值
    PRIMARY KEY (trade_date, wave_id)
);
