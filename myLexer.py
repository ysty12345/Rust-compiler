import json
from string import digits, ascii_letters
from tokenType import tokenType, tokenSymbols, tokenKeywords

def enum_to_str(obj):
    if isinstance(obj, tokenType):
        return obj.value  # 或者 obj.name
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

class DFA_state(object):
    def __init__(self):
        self.transfer = {}
        self.tokenType = tokenType.UNKNOWN


class DFA(object):
    def __init__(self) -> None:
        self.root = DFA_state()
        self.cur = self.root
        self.len = 0

        self.initAlpha()
        self.initSymbol()
        self.initDigit()

    def initAlpha(self):
        # 初始化所有的keyword对应的状态，并记录状态集合
        stateSet = set()
        for keyword in tokenKeywords:
            stateSet |= self.initToken(keyword, tokenKeywords[keyword])

        # 处理剩余的字母、数字转移，应该识别为identifier
        identifierState = DFA_state()
        identifierState.tokenType = tokenType.IDENTIFIER

        for letter in ascii_letters + digits + "_":
            identifierState.transfer[letter] = identifierState

        for alpha in ascii_letters + "_":
            if alpha not in self.root.transfer:
                self.root.transfer[alpha] = identifierState

        for state in stateSet:
            # 不是单词末尾，则类型为identifier
            state.tokenType = (
                state.tokenType
                if state.tokenType != tokenType.UNKNOWN
                else tokenType.IDENTIFIER
            )
            for alpha in ascii_letters + "_":
                if alpha not in state.transfer:
                    state.transfer[alpha] = identifierState
            for d in digits:
                if d not in state.transfer:
                    state.transfer[d] = identifierState

    def initSymbol(self):
        # 初始化所有的符号
        for symbol in tokenSymbols:
            self.initToken(symbol, tokenSymbols[symbol])

    # 为整型、浮点型常量添加对应的状态与转移
    def initDigit(self):
        # DFA的状态转移图详见报告
        states = {}

        # 建立6个新状态
        for i in range(7):
            if i == 0:
                states[i] = self.root
            else:
                states[i] = DFA_state()

        # 设置接受态
        states[1].tokenType = tokenType.INTEGER_CONSTANT
        states[3].tokenType = tokenType.FLOATING_POINT_CONSTANT
        states[6].tokenType = tokenType.FLOATING_POINT_CONSTANT

        # 添加所有0-9的转移
        for d in digits:
            states[0].transfer[d] = states[1]
            states[1].transfer[d] = states[1]
            states[2].transfer[d] = states[3]
            states[3].transfer[d] = states[3]
            states[4].transfer[d] = states[6]
            states[5].transfer[d] = states[6]
            states[6].transfer[d] = states[6]

        # 添加其余琐碎转移
        # states[1].transfer["."] = states[2] # 支持浮点数
        states[1].transfer["e"] = states[4]
        states[1].transfer["E"] = states[4]
        states[3].transfer["e"] = states[4]
        states[3].transfer["E"] = states[4]
        states[4].transfer["+"] = states[5]
        states[4].transfer["-"] = states[5]
    def initToken(self, word: str, type):
        cur = self.root
        stateSet = set()
        for char in word:
            if char not in cur.transfer:
                cur.transfer[char] = DFA_state()
            cur = cur.transfer[char]
            stateSet.add(cur)
        cur.tokenType = type
        return stateSet

    def forward(self, ch: str):
        '''返回当前状态的tokenType和当前状态的长度'''
        assert len(ch) == 1, "Expect a char, got a string"
        self.len += 1
        if ch not in self.cur.transfer:
            self.reset()
            return None, 0
        else:
            self.cur = self.cur.transfer[ch]
            return self.cur.tokenType, self.len

    def reset(self):
        self.cur = self.root
        self.len = 0


class Lexer(object):
    def __init__(self) -> None:
        self.dfa = DFA()

    def getLex(self, lines):
        ret = []
        row = 1
        id = 1
        annotation = False
        success = True
        for line in lines:
            if not line.strip():
                continue
            self.dfa.reset()
            token_type = None
            length = 0
            col = 0
            for ch in line + "#":  # 行末加一个字符以确认每一行最后一个输入DFA的串
                newtoken_type, newlength = self.dfa.forward(ch)

                if token_type and not newtoken_type:
                    if token_type == tokenType.S_COMMENT:
                        break
                    elif token_type == tokenType.LM_COMMENT:
                        annotation = True

                    if not annotation:
                        item = {}
                        item["id"] = id
                        id += 1
                        item["content"] = line[col - length : col]
                        item["prop"] = token_type
                        item["loc"] = {"row": row, "col": col - length + 1}
                        ret.append(item)

                    if token_type == tokenType.RM_COMMENT:
                        annotation = False

                    self.dfa.reset()
                    token_type, length = self.dfa.forward(ch)
                    # 重读依然失败
                    if not token_type and not annotation and ch not in [" ", "\t", "\n"]:
                        item = {}
                        item["prop"] = tokenType.UNKNOWN
                        item["loc"] = {"row": row, "col": col + 1}
                        ret.append(item)
                elif not token_type and not newtoken_type:
                    if not annotation and ch not in [" ", "\t", "\n"]:
                        # 无法解析的字符
                        success = False
                        item = {}
                        item["prop"] = tokenType.UNKNOWN
                        item["loc"] = {"row": row, "col": col + 1}
                        ret.append(item)
                else:
                    token_type, length = newtoken_type, newlength
                col += 1
            row += 1

        ret.append(
            {
                "id": id,
                "content": "#",
                "prop": tokenType.EOF,
                "loc": {"row": row, "col": 1},
            }
        )
        # ret = json.dumps(ret)
        # 写入 JSON 文件
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(ret, f, indent=4, ensure_ascii=False, default=enum_to_str)
        return ret, success
