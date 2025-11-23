import random

# --- 基础定义 ---
SUITS = ['♠️', '♥️', '♣️', '♦️']
# 2-9, 10, J=11, Q=12, K=13, A=14
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
VALUES = {r: i+2 for i, r in enumerate(RANKS)}

def get_deck():
    """生成一副52张标准扑克牌"""
    return [{'rank': r, 'suit': s, 'val': VALUES[r], 'text': f"{s}{r}"} for s in SUITS for r in RANKS]

# ==========================================
# 🧠 核心算法：牌力计算器 (ZJH)
# ==========================================
def calculate_zjh_score(cards):
    """
    为任何3张牌计算一个绝对分值。
    算法保证：Score(A) > Score(B) 当且仅当 牌型A > 牌型B。
    分值结构 (Base 15): Type * 16^3 + Card1 * 16^2 + Card2 * 16^1 + Card3
    类型权重: 
    6: 豹子 (Leopard)
    5: 同花顺 (Straight Flush)
    4: 同花 (Flush)
    3: 顺子 (Straight)
    2: 对子 (Pair)
    1: 散牌 (High Card)
    """
    # 1. 预处理：排序（从大到小）
    sorted_cards = sorted(cards, key=lambda x: x['val'], reverse=True)
    v1, v2, v3 = sorted_cards[0]['val'], sorted_cards[1]['val'], sorted_cards[2]['val']
    
    is_flush = (cards[0]['suit'] == cards[1]['suit'] == cards[2]['suit'])
    is_straight = (v1 - v2 == 1 and v2 - v3 == 1)
    # 特殊顺子 A,2,3 (14,3,2) -> 视为最小顺子
    if v1 == 14 and v2 == 3 and v3 == 2:
        is_straight = True
        # 调整顺序用于比较：3, 2, 1 (A当做1)
        v1, v2, v3 = 3, 2, 1 

    # 2. 判定牌型并计算基础分
    # 豹子
    if v1 == v2 == v3:
        hand_type = 6
        score_val = v1 # 豹子只看一张牌
    # 同花顺
    elif is_flush and is_straight:
        hand_type = 5
        score_val = v1 # 同花顺只看最大牌
    # 同花
    elif is_flush:
        hand_type = 4
        score_val = v1 * 256 + v2 * 16 + v3 # 同花比大小: 先比第一张, 再比第二张...
    # 顺子
    elif is_straight:
        hand_type = 3
        score_val = v1
    # 对子
    elif v1 == v2: # 对子在前面 (e.g., K, K, 5)
        hand_type = 2
        score_val = v1 * 16 + v3 # 先比对子大小(v1), 再比单张(v3)
    elif v2 == v3: # 对子在后面 (e.g., A, 8, 8) -> 排序后是 A, 8, 8
        hand_type = 2
        score_val = v2 * 16 + v1 # 先比对子(v2), 再比单张(v1)
    elif v1 == v3: # 理论上排序后不可能出现 v1==v3 但 v2不等的情况
        hand_type = 2
        score_val = v1 * 16 + v2
    # 散牌
    else:
        hand_type = 1
        score_val = v1 * 256 + v2 * 16 + v3

    # 3. 生成最终绝对分数
    # 乘以一个巨大的系数确保牌型(Type)是最高优先级
    final_score = hand_type * 1000000 + score_val
    return final_score, _get_hand_description(hand_type, v1, v2)

def _get_hand_description(hand_type, v1, v2):
    """生成友好的牌型名称"""
    rank_map = {11:'J', 12:'Q', 13:'K', 14:'A'}
    def r(val): return rank_map.get(val, str(val))
    
    if hand_type == 6: return f"豹子 ({r(v1)})"
    if hand_type == 5: return f"同花顺 ({r(v1)}高)"
    if hand_type == 4: return f"同花 ({r(v1)}高)"
    if hand_type == 3: return f"顺子 ({r(v1)}高)"
    if hand_type == 2: return f"对子 ({r(v1)})" # 这里v1是对子的数值
    return f"散牌 ({r(v1)}高)"


# ==========================================
# 🃏 牌组生成器
# ==========================================
def get_random_hand():
    """完全随机生成一副手牌"""
    deck = get_deck()
    return random.sample(deck, 3)

def generate_rigged_hands_zjh(luck_rate):
    """
    生成扎金花手牌，包含黑幕逻辑。
    逻辑：不再是捏造假牌，而是“一直发牌直到满足黑幕条件”。
    """
    
    # 1. 先给玩家发一副牌 (基于概率，大部分时候是散牌，偶尔有好牌)
    # 为了游戏体验，我们可以微调玩家的牌，让他不要太烂，否则他不敢加注
    # 比如：强制给玩家 20% 概率发对子以上
    if random.random() < 0.2:
        p_cards = _force_generate_good_hand() # 强行发好牌
    else:
        p_cards = get_random_hand()
        
    p_score, p_desc = calculate_zjh_score(p_cards)
    
    # 2. 决定这一局的命运 (输还是赢)
    # luck_rate 越低，越容易遇到“冤家牌” (Bad Beat)
    should_win = False
    is_bad_beat = False # 是否触发冤家局 (你很大，但我刚好压你)
    
    rng = random.random()
    if rng < luck_rate * 0.5: # 0.5是基础胜率，运气好则提升
        should_win = True
    else:
        # 运气不好，输。
        # 如果运气极差 (<0. xx) 且玩家牌不错 (>对子)，触发冤家局
        if rng*luck_rate < 0.4 and p_score > 2000000: 
            is_bad_beat = True
            
    # 3. 根据命运生成庄家的牌
    # 我们使用“碰撞法”：不断随机发牌，直到满足条件
    d_cards = []
    d_score = 0
    d_desc = ""
    
    attempts = 0
    while attempts < 200: # 防止死循环
        d_cards = get_random_hand()
        d_score, d_desc = calculate_zjh_score(d_cards)
        
        # 避免重复：庄家的牌不能和玩家的牌一样（真实扑克里只有一副牌）
        # 这里简单判断：如果花色和点数完全一样则重发
        if _check_cards_overlap(p_cards, d_cards):
            continue

        if should_win:
            # 玩家赢：庄家分数必须小
            if d_score < p_score:
                break
        else:
            # 玩家输
            if is_bad_beat:
                # 冤家局：庄家必须赢，而且不能赢太多 (制造惜败感)
                # 比如：分差在一定范围内，且必须是同一种大牌型或者刚好压一头
                # 这里简化：只要赢了就行，概率上大概率是普通赢，偶尔是冤家
                if d_score > p_score:
                    break
            else:
                # 普通输：只要庄家大就行
                if d_score > p_score:
                    break
        attempts += 1
    
    # 如果尝试200次都没随机出想要的结果（极少见），强制给庄家发豹子兜底
    if attempts >= 200:
         d_cards = [{'rank':'A','suit':'♠️','val':14},{'rank':'A','suit':'♥️','val':14},{'rank':'A','suit':'♣️','val':14}]
         d_score, d_desc = calculate_zjh_score(d_cards)

    return p_cards, d_cards, p_score, d_score

def _force_generate_good_hand():
    """辅助：强行生成一副对子或以上的牌，增加游戏刺激度"""
    while True:
        cards = get_random_hand()
        score, _ = calculate_zjh_score(cards)
        if score > 2000000: # 2000000 是对子的起步分
            return cards

def _check_cards_overlap(hand1, hand2):
    """检查两副牌是否有重复的牌（物理上不可能）"""
    set1 = set(f"{c['suit']}{c['rank']}" for c in hand1)
    set2 = set(f"{c['suit']}{c['rank']}" for c in hand2)
    return not set1.isdisjoint(set2)

# ==========================================
# 21点 逻辑 (保持原样或微调)
# ==========================================
def deal_blackjack_card(current_hand_val, luck_rate):
    """21点发牌逻辑"""
    deck = get_deck()
    card = random.choice(deck)
    # 这里可以保留之前的控制爆牌逻辑，不再赘述
    return card

def score_blackjack(hand):
    """21点算分"""
    score = 0
    aces = 0
    for card in hand:
        val = card['val']
        if val >= 10 and val <= 13: score += 10
        elif val == 14: score += 11; aces += 1
        else: score += val
    while score > 21 and aces:
        score -= 10; aces -= 1
    return score