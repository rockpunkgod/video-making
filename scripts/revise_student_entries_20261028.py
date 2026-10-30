"""Emit an explicit patch for an editorial-only revision; never modify ANSWER.

Semantic method versions and all decision/source/role fields are preserved.
The reviewed prior inventory is required and must still match byte-for-byte.
Apply emitted patch, then use the normal projection generator.
"""
import argparse
import hashlib
import json
from pathlib import Path
from copy import deepcopy
import yaml
import difflib

ROOT=Path(__file__).resolve().parents[1]
REVISION="2026-10-28.2"
# Each short entry is individually authored. Examples are relation/structure
# illustrations, NOT invented exam questions or additional accepted Cases.
COPY = """
R01|选项多说一截？先拆原文已支持的A和新增B；B无直接或间接依据才排。|只说参加，却多出为了获奖，要另查获奖目的。|A没核实先不拆；B有支持不能排，排一项不证明另一项。
R02|词都认识还分不清？圈谁和完整动作，只核本题换了哪处；一致不等于答案。|希望帮助不等于已经帮助，要把希望一起圈。|无偷换停本法；共同主体省略不算偷换。
R03|换了词就认不出？并排核同一对象与完整意思；同词或近义命中还不能选。|都是支持，一个指能力，一个指意愿，意思仍不同。|词义或条件不清先补证，不凭对应词数量定案。
R04|比较项总看混？先写谁跟谁比哪一点，再核方向和范围；最高级不自动错。|同一对象比速度，不能换成比价格。|未定位不算证伪；最高级有充分支持就不能排。
R05|原因结果选反？先圈题干问哪一环，再核同一因果链；不是总选最后结果。|题干问为什么，不能把最后发生的结果当原因。|两项或链条缺依据就停，先后不证明因果。
R06|主旨项相关却不全？对照已核核心指出遗漏；近义或概括能覆盖就别排。|全文重点是问题及解决，候选只说问题，要核它是否漏掉解决关系。|核心未核好先停；不是缺原词就缺内容。
R07|并列项想一起删？先框同层内容、核题干问谁；只问一项就拆开。|同列两种用途，题干只问其中一种，不能打包排除。|and不证明同层，也不能因位于转折前共同排除。
R08|例子题卡住？先分例中事实和举例作用，再找它支持的观点；不见细节就排。|问实验发生什么，细节本身可能就是所问。|直接问例中事实时不用本法排细节。
R09|全文框架卡住？先题干与相关选项，再核正文压三格；骨架不是答案。|首段反复讲背景，不代表背景就是全文判断。|缺主要段落或只问局部不启动；没重复词可跳过该线索。
R10|代词指谁拿不准？把可能所指换回完整句核角色；最近的名词不一定对。|两个名词都合单复数，只有一个能做句中动作。|数一致不够；所指可能是一件事或状态，不硬找最近名词。
R11|长句读乱了？先圈谁和完整谓语，暂划修饰再恢复关键条件；拆句不等于删信息。|条件从句改变动作成立范围，拆完还得放回。|否定、条件和范围不能删；含义不清不继续判项。
R12|找不到出处？圈题干对象与有区别的标志，只标待查位置；定位不是答案。|同一个数字出现在不同人的事件里，命中还要核对象。|特定跳读版须满足自身前提，不把同词或一题一段当证据。
R13|人物名出现好多次？圈区别名词再找对应动作，只定位不定案。|同一个人先后有两种状态，要查题干问的阶段。|名词无区别就换动作线索，不按次数或最近位置选。
R14|不知道去哪段找？借相邻题已确认出处暂估区间；找到区间还得核本题。|文章中间回叙，当前证据可能落在暂估区间之外。|插叙、共享出处或区间外证据出现就取消锁区。
R15|动词一样却选不准？并排核谁对谁做什么，保留否定和条件；同动作词不等于同关系。|都写帮助，但帮助者与被帮助者可能互换。|主体、对象或动作义不明先补证，关系一致不代表整项正确。
R16|主旨选项都谈同一件事？先圈所问范围，再比各项不同判断；共同话题不等于主旨。|题干问一段，全文概括再广也未必概括了这一段。|先分全文与段落，不凭词频、范围更大或剩一项选。
R17|定位句还说不清？先写缺哪个问题，只为它扩读；补到关系再回原断言核。|邻句虽然提同一人，却没解释所问原因，不算补上证据。|已有证据够用就停扩读；材料仍缺就暂留，不编联系。
F01|七项乱试？句型、主角、时间各查一次再回文；无区别也记录，分组不定案。|两个祈使句都对父母说，却可能建议完全不同的事。|无区别不编组；新证据可纠错，不重演三分或靠占用选。
F02|句型像就想填？先按完整句、半句等分组；结构都能接就回正文比内容。|两个都是祈使句，动作对象却不同。|大小写仅辅助；同句型不证明内容接通。
F03|都说同一人却拿不准？先分主角，再核具体对象与动作；同主角不等于能填。|省略的你都是父母，处理的却是不同问题。|代词所指不明暂留；可更正初筛，不重复整套分组。
F04|想按过去时筛答案？先圈真谓语，再核当前事件时间；词尾相同不算同阶段。|过去经历后接一般感悟，不能只留过去式候选。|分词不承担句子时态；无差异如实记，不凭同组定案。
F05|段首空不知选谁？先标它管哪些内容，再核是否都能统领；概括大不自动对。|一项只概括一个例子，不能统领后面所有分项。|段首位置和Here are不定案，局部匹配不够。
F06|看到同词就想选？连出两处呼应并写清指什么，再放回两侧；重词不等于答案。|两个候选都提同一词，但只有一个动作接住空前条件。|没有具体呼应不硬套；同词多项仍要比完整关系。
F07|连接词看懂仍犹豫？写两侧在说什么，再核真实关系；只接前句不算通过。|事后补救不能代替空位所需的事前准备。|前后任一侧冲突就停；不能只凭连接词定关系。
F08|褒贬词让你想直接选？圈评价谁和否定范围，只暂分方向；同向不算答案。|说困难可能是为了给帮助，不是在否定对象价值。|中性不强分，方向相同仍要比具体措施和功能。
F09|半句空怕接错？先把候选拼成一句，再核对象与意思；语法接通不等于内容成立。|两项都补成完整句，一项却换了动作对象。|大小写或句长不定案；都能补句就停结构筛选。
F10|填完仍不放心？逐空回填，再查未选项的内容；选项已用不证明当前位置错。|某项填在别处但那处尚未核实，仍要回查两个位置。|内容仍多项成立就暂留，不能拿占用或剩余作证据。
F11|两项都能接一句？分别核空前条件、空后结果和整段任务；只通一侧不定案。|两项都像原因，要回空前限定看究竟解决哪个问题。|两项仍成立就留缺口，不凭更像原因或剩一项选。
C01|完形不知道查哪儿？先标空的作用、圈近处提示，不足再扩读；线索路径不是答案。|人物态度乐观，不代表实际遭遇顺利。|词义或关系没闭合先留空，找到独立提示再返回。
C02|空前读通还犹豫？核两侧对象和动作，不足再扩读；猜出的邻空不能互证。|两个待定空互相解释，不等于有独立文本证据。|线索冲突或仍缺证据先暂留，不截取只支持初选的一句。
C03|开头读完没方向？先记人物和背景形成粗框架；不能据基调猜后续情节。|首句乐观，后文仍可能出现困难。|首句没说的不编；局部已闭合不必每空重讲首句。
C04|不知找哪类提示？先看空修饰谁或谁在行动，再找同一对象的线索；词性不定答案。|同为形容词，一个写情感，一个写客观状态。|修饰对象、动作归属或具体词义不明先停。
C05|近义项总犹豫？写各项具体状态、程度或功能，配当前对象；中文近义不算等值。|情感投入不等于客观状态，两种积极评价也可能不同。|词义或搭配不明先留缺口，不凭主旨强选。
C06|时间关系绕晕？写两件事何时发生和已给间隔；先后不等于因果。|身份变化并不能证明经历时长变化。|没给时间就标未知，不补时长或原因。
C07|看见重复词就想填？先核两处是否仍指同一对象；复现只给线索。|相同名词可能指不同事件，不是同一件事重现。|未知词根不拆猜，同词或同后缀不能单独定案。
C08|想从好结果倒推？先写它评价哪项行为，再核候选联系；不是积极词都能填。|两个积极词评价不同方面，结果只支持其中一类。|评价对象或桥接不清先停，不用猜定空作证据。
C09|动作连着却选不稳？画已有动作链，逐箭头找依据；动作多不证明因果。|各句都通，但动作对象不同，整段可能接不成过程。|没有依据的边留空，不补动作、时长或因果。
G01|看到空先别变词。标有无提示，再圈位置需要什么；这里只定路线，不填答案。|environmental ___ (protect)要核名词中心，不能见protect就走动词路线。|功能不明先补完整句；到节点后改用具体规则。
G02|看到提示词就想变？先标有提示或无提示，再核位置；分路不是答案。|两句结构都完整，空位也可能需要连接副词。|无提示不锁死四类；未确认功能不开始变形。
G03|冠词犹豫？圈名词中心，核数和所指；有后置修饰不自动填the。|后接of不等于所指唯一，仍须核特指泛指。|已有其他限定或所指不清先停，a/an看读音。
G04|代词怎么变？先找指谁，再标这个位置的作用；介词后不一律宾格。|名词省略时可能需要独立物主形式，不能只按前面的介词选。|所指或省略不清就停，形式it不硬找实体所指。
G05|介词总凭感觉？圈动作和后面中心词，核搭配与关系；未知搭配先停。|增加了多少与增加到多少，关系不同，by和to不能混用。|对象多不自动among，中文意思不能唯一决定介词。
G06|从句词不会选？划分句、标缺口，再核连接作用；地点词不自动配where。|地点名词后的从句若缺宾语，不能只因地点就用where。|类型、缺口或语义不清先停，不见完整句就填that。
G07|两句之间不会填？写两侧意思，再核关系、词类和标点；逗号不决定词。|都译作转折，连接词与连接副词在句中功能仍不同。|句子成分不完整先回从句判断，不能只凭中文转折选词。
G08|提示词不知道怎么变？圈空位支配和修饰关系，先定词类；原词性不是答案词性。|动词protect可在相应结构中派生成名词，不先走非谓语。|主干不清先拆句，名词性位置也可能容纳动名词。
G09|名词空不知怎么变？先核结构，再查数和所属；名词性位置不排所有doing。|environmental protection与After spending的结构不同。|介词后不一律派生名词或doing，搭配不明先停。
G10|形副和等级看乱？先圈修饰谁，再核真实比较；不按人或物机械选-ed/-ing。|修饰名词也可能用另一个名词，不能一律改形容词。|无等级差异不造比较级，状态与搭配不明先核。
G11|数词怎么变？先判数多少还是第几，再核结构；数字本身不决定序数。|同一数字在不同位置可表示数量或次序。|所指或功能不清先停，the也不能单独证明序数。
G12|谓语非谓语分不清？确认要动词后先划本分句；全句有动词不证明本空非谓语。|主句已有谓语，从句仍可能需要自己的谓语。|未判空位功能或分句边界先停，不只数全句动词。
G13|谓语形式犹豫？核时间、主被动与参照，再查真主语；时间词不独立定案。|since或by只提供线索，仍须核事件参照和真实语态。|角色或时间参照不明先停，不用有be无be口诀选形。
G14|主谓一致拿不准？划开修饰圈真主语；最近名词不一定是中心，本步不定时态。|主语旁有复数修饰，也不能忽略真正的单数中心。|特殊数量或集合结构须另核，不能只按距离选主语。
G15|非谓语只会猜词尾？依次核作用、谁做和相对时间；逗号不决定doing。|有逗号仍可能需不同非谓语形式，要核句法和主被动。|一轴不明先停，相对时间不套绝对现在或过去。
G16|动作主人找不准？先标非谓语作什么成分，再圈谁执行或承受；最近名词不是证明。|作状语的非谓语，主人不一定是旁边修饰短语中的名词。|归属冲突先查独立结构，不自己补一个主人。
G17|长句找不出空位？先圈主干和空在哪，再恢复关键结构；暂划不是删除。|空实际在从句里，删掉从句就看不出空位功能。|主干不足先恢复相关从句，不先填后倒贴成分。
G18|做完发现考点重复？只圈出并回查各空证据；一般不重复不等于禁止重复。|两个空都获独立结构支持，不能为凑分布改一个。|重复只触发核验，不能推翻本句充分证据。
G19|觉得变形次数不对？写原词到拟填词的路线，再回查结构；次数不决定词形。|名词变复数仍是名词，不必强换词类。|一般一次只是提示，不因次数撤销有据词形。
A01|作文读着顺却怕漏点？把题面要求逐条对回原稿，先补任务；五检不是扣分表。|邀请目的写了，时间地点没交代，要先补活动安排。|无题目只校语言，无全文不做整篇诊断。
A02|应用文无从下笔？先圈限定与要点，再写准确基础句；六步是支架，不保分。|感谢任务不能照搬邀请结尾，模板须随目的改变。|基础内容没成立先修，不强塞复杂句。
A03|想到了却写不成句？先写谁和做什么，再补必要细节；准确简单句先保留。|同一个要点先有完整主干，再加题面允许的时间地点。|主体或动作不清先回要点，不编背景凑细节。
A04|想合长句？先各写正确简单句，再核真实关系；合不稳就保留独立句。|两个动作主体不同，不能随便省略主体接成非谓语。|基础句或关系不成立不合并，不凑从句数量。
A05|中文信息挤成一团？先分核心和限定再重排；语序能改，原义和条件不能丢。|句首条件决定动作何时成立，重组不能把它删掉。|核心没清楚先停，按信息难度而非整篇词数选法。
A06|总背范文却不会用？先自己译一句再对照，只记表达缺口；准确异写不用改错。|自译和范文用词不同但意思搭配都对，可以保留。|范文或AI改了意思就不抄，AI升级可选。
A07|简单句想拼起来？圈共同主体和真实关系，再选一种合适连接；不会合就先不合。|原来没有因果的两件事，不能靠because造出因果。|主体或依附不成立退回独立句，不为复杂而强拼。
A08|文体格式拿不准？先圈写给谁和写作目的，再安排段落任务；骨架不是要点。|感谢和邀请的结尾任务不同，不能照搬同一模板。|题面给了特殊格式先遵守，不强套段数或句型。
A09|想给作文打分？先核题目和全文，再按内容语言结构定档；不按错误数或字体美观算分。|只有转写文本时，不能判断原书写是否影响交际。|缺题目或全文不给完整分，限对应15分规范。
A10|练作文不知道先练啥？从现稿挑一个真实缺口，只练下一小步；背得多不保证分高。|基础句仍错，就先练准确表达，不先堆高级词。|无现稿不承诺档次，训练数量不是单篇配额。
W01|续写不知道往哪走？先读两首句、回原文找约束，再搭两段；框架不是唯一剧情。|积极结局也不能靠突然出现的无铺垫救场者成立。|缺原文或首句先停完整构思，不拿升华补因果。
W02|两段不会接？先列接句、必要桥、接续、结局、回应五格提纲；有据才填。|提纲已合理接上第二首句，就不再补一段重复过渡。|不凑十句，给定首句不必抄，独立升华句非必需。
W03|剧情整理不清？按本次固定四格填已知、留未知；四格只是约束，不是现成故事。|原文说明想参加一项活动，没说明如何参加，目的格可填，方式格先留空。|教师先定版本；无依据先空着，不凭口诀编事故。
W04|第一段不知写到哪？圈第二首句的已知状态，回文找必要过程；缺口不等于随意编。|第二首句人已到场，只限定此前需合理走到到场。|能自然衔接就不强补过程，不让每个名词各占一句。
W05|动作写得太笼统？拆真实相连的小动作，核人物能力；不为凑三步加动作。|一个动作已够推进，不必强拆成奔跑、跳跃、拥抱。|原行动没成立不拆，能力或因果冲突先撤回。
W06|续写不知抓什么？圈核心人物、矛盾和关键线索，只标出处；线索不是解决方案。|圈到一个物件，还要核它凭什么能帮助解决问题。|找不到就留缺口，不编主角或事故补三点。
W07|想让前后呼应？把关键行为连回一条原文线索，说明作用；重复同词不算回扣。|物件结尾再出现，却没影响行为或结果，不等于兑现用途。|不用每个物件，不为回扣添无据能力或人物。
W08|故事跳得太快？写因为A、行动B、结果C，逐条核联系；先后不是因果。|两事相继发生，却没有促使行动的联系，不能用所以硬连。|物理条件或动机不成立就停，不拿新结果证明旧猜测。
W09|故事有了却没画面？在有效行动旁加一处有用细节；不要求动作神态环境全加。|一个环境细节能显示人物处境，就不必再堆同类修饰。|先修框架，不凑字数，不把专项模板位置当通用禁令。
W10|相邻句接得别扭？圈共同对象、回填代词，再核动作接续；不为无痕删必要逻辑。|两个人都能被he指代时，先明说具体人物。|有歧义先明确，删词会改转折或因果就保留。
W11|觉得故事需要波折？先核有无铺垫；过程已合理完整，就不必硬加小障碍。|原文没铺垫的关键救场者，不能因结局向好就加入。|基础框架未完整先停，波折不是每篇必写。
W12|想换高级词？先说清实际动作和力度，确认搭配才换；准确常用词可以不动。|同为抓住，握持力度和情境不同，不随词表逐个替换。|含义或搭配没把握保留原词，不按替换数量评分。
W13|结尾只会喊道理？先把解决结果连回原文矛盾；故事能回应就不硬加升华句。|结局行动已呈现成长，不必另塞一句泛泛感悟。|核心矛盾未解先修情节，不用口号代替结果。
W14|不知哪句该扩写？先保衔接和解决的骨架，再选有依据的细节；肌肉句也不能乱编。|非功能位突然加新事故，同样会破坏原文约束。|骨架未接通先补功能，不按固定句数分好坏。
W15|续写想评分？先核原文、两首句和自写全文，再评整体；不抄首句不算缺项。|故事自然回应主题，即使没有独立升华句也不能机械降档。|缺材料不给完整分，限对应25分规范，不编固定扣分。
W16|续写练不动？先看现稿是否完整顺因果，只选一处改；高阶句型不是第一步。|段间还缺桥，就先练桥接，不先增加更多句式。|基础未稳不跳升级，不强加转折、动作或升华配额。
""".strip()

ROLE_RESULT={
    "locator":"是待查位置，不直接得答案。",
    "interpreter":"是对当前关系或表达的解释，还要核完整题目。",
    "reducer":"是优先核查的范围，不直接得答案。",
    "decider":"是当前候选的保留、排除或待定判断；不能由剩余项自动定案。",
    "verifier":"是对已有候选或稿件的核验，不替代独立证据。",
    "framework":"是待核框架或计划，不是答案或分数。",
}
FIRST_SUFFIX={
    "F01":"接着核主角和真谓语时间，三维各一次，无区别也标无区分度；分完回正文。",
    "G01":"没有提示词去功能词路线；有提示词先判位置需要什么，确认要动词才分谓语与非谓语。",
    "R09":"共同概念只作假设；再读有效首尾，最后看中间段首及必要回答或段尾，回全文核三格。",
    "G12":"随后圈本分句已有谓语和连接手段，再定谓语或非谓语路线，不定最终形式。",
    "G15":"随后核逻辑主语与主被动，再以谓语为参照核先后；三轴不省略。",
}
PREREQ={
    "R":"先读清题干所问对象，能说明当前这句谁做什么；挡住判断的词不认识，先标出求助，不用词面相似代替句意。",
    "F":"先分清一句是否说完整，再找句中实际谈谁。真谓语就是承担本句时间的动词；-ed或-ing词尾本身不能证明它是谓语。",
    "C":"先读出本空两侧谁在做什么，区分题面已说与自己猜的内容；决定候选的词义不明就先标出来。",
    "G":"先把空保留不填，圈本句动作和对应的人或物。主语是谁或什么，谓语是这句的完整动作或状态；分不清先核完整句。",
    "A":"先读清写给谁、要完成哪件事。基础句先做到谁、做什么或是什么清楚；准确简单句可以保留。",
    "W":"先备齐原文与两段首句，分清原文已发生与自己准备写的内容；可以先用中文标功能，不急着写复杂英文。",
}

def sentence(text):
    text=text.strip()
    return text if not text or text[-1] in '。？！.!?' else text+'。'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review",type=Path,required=True)
    parser.add_argument("--method-file",required=True)
    parser.add_argument("--refine",action="store_true")
    args=parser.parse_args()
    review=json.loads(args.review.read_text(encoding="utf-8"))
    for rel,h in review["input_snapshot"].items():
        if rel!=args.method_file:
            continue
        if not args.refine and hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=h:
            raise ValueError("Reviewed input changed: "+rel)
    proposed={r["method_id"]:r for r in review["methods"]}
    copy={line.split("|",1)[0]:line.split("|")[1:] for line in COPY.splitlines()}
    if set(copy)!=set(proposed) or len(copy)!=82:
        raise ValueError("Must author all82 rows")
    indexpath=ROOT/"method-registry/registry.yaml"
    idx=yaml.safe_load(indexpath.read_text(encoding="utf-8"))
    patches=[]
    for rel in idx["method_files"]:
        if rel!=args.method_file:
            continue
        path=ROOT/rel; old=path.read_text(encoding="utf-8")
        document=yaml.safe_load(old)
        for m in document["methods"]:
            mid=m["method_id"]
            history=f"method-registry/history/{mid}/editorial-before-20261028.yaml"
            if args.refine:
                current_revision=m['full'].get('presentation_revision')
                assert current_revision in ('2026-10-28.1',REVISION),mid
                if current_revision=='2026-10-28.1':
                    prior=f'method-registry/history/{mid}/editorial-20261028.1.yaml'
                    if (ROOT/prior).exists(): raise ValueError('Prior presentation already archived: '+mid)
                    patches.append(('add',prior,yaml.safe_dump(m,allow_unicode=True,sort_keys=False)))
                previous=yaml.safe_load((ROOT/history).read_text(encoding='utf-8'))
                m.clear(); m.update(deepcopy(previous))
            else:
                previous=deepcopy(m)
                if (ROOT/history).exists(): raise ValueError("History exists; refuse overwrite: "+mid)
                patches.append(("add",history,yaml.safe_dump(previous,allow_unicode=True,sort_keys=False)))
            ten,example,shortstop=copy[mid]
            first=proposed[mid]["low_floor_support_proposal"]["first_micro_action"]
            if mid=="F01":
                first="先在A-G旁标完整句、半句或祈使等真实句型，先不填空。"
            if mid=="W02":
                first="还未动笔就先列中文提纲，已有稿则在现稿标接句、必要桥、接续、结局与回应；不先凑十句。"
            if mid=="W03":
                first="按教师为本次固定的目的、方式、困难、结局四格，先圈原文已经明示的一格，未知的留空。"
                m["challenge_prompt"]="先不写故事。按本次已固定的四格，把两首句已知与原文约束填进去，未知处留空；给已填的一格指出原文依据。"
            if mid=="R01":
                m["four_step_card"]["start"]="当前候选有可确认的原文共同核心，又可能多说一截；两个选项都像原文是常见卡点，不是必须同时出现的条件。"
            extra=FIRST_SUFFIX.get(mid,"")
            result=ROLE_RESULT[m["primary_role"]]
            if mid=="G01":result="只是下一知识节点；到节点后用具体句法、搭配和句意求证，不是词形答案。"
            if mid=="R09":result="只是全文骨架卡：对象、核心判断、结构任务；三格都须正文支持，不直接定答案。"
            if mid=="W02":result="是中文功能提纲或现稿的功能缺口，不是成稿或分数。"
            support={
                "first_micro_action":first,
                "prerequisite":PREREQ[mid[0]],
                "if_stuck":proposed[mid]["low_floor_support_proposal"]["if_stuck"],
                "example":example,
                "example_scope":"关系/结构示意，非完整试题，不计真题或已验案例。",
                "micro_action_is_not_completion":"完成第一小步不等于完整方法成功；继续完成四步卡的判断与停止核验。",
                "short_stop":shortstop,
            }
            if mid=="R02":
                support["legacy_entry_note"]="旧称三槽位核对可帮助认出入口，不要求每题固定三格；只核本题主体、施受、愿望/事实或能力/意愿的实际差异。"
            if mid=="W03":
                support["legacy_entry_note"]="教师层先固定寒8板书这一来源版本。其他PTSD版本仍留在完整源契约，不能混槽；学生不必先比较课次才能练本次动作。"
                support['student_four_step_card']={
                    'start':'原文和两段首句齐备，要把故事已知条件整理成四格。',
                    'first_cut':first,
                    'judge':'把原文或首句已经说明的目的、方式、困难、结局写进对应格；没说明的标未知，不把四格写满当成故事成立。',
                    'stop':'本次用哪四格尚未给清就先确认；找不到依据先留空，不编事故或救场者。'}
                support['student_visual_formula']='本次四格：目的 | 方式 | 困难 | 结局\n原文/首句已说明 → 填入并标出处\n未说明 → 留空待证\n四格填满 ≠ 情节成立'
                support['student_counterexamples']=['为把困难格填满而编事故，四格虽然齐全，却没有原文依据，不能据此推进故事。']
            m["full"]["beginner_support"]=support
            m["full"]["presentation_revision"]=REVISION
            m["compact"]["10s"]=ten
            opening=ten.split("？",1)[0]+"？" if "？" in ten else ten.split("。",1)[0]+"。"
            m["compact"]["30s"]=opening+first+extra+"例如，"+example+shortstop
            # Full stop remains exposed here and on the four-step card; short
            # copy is a target-duration draft, never a timing certificate.
            action=m["core_action"]
            decision=m['decision_rule']; spoken_stop=m['stop_rule']; counter=m['counterexamples'][0]
            if mid=="W03":
                action=first
                decision=support['student_four_step_card']['judge']
                spoken_stop=support['student_four_step_card']['stop']
                counter='为了把困难格填满而编一个事故，虽然格子齐了，却没有原文依据，不能据此推进故事。'
            m["compact"]["90s"]=opening+sentence(action)+"这一步得到的"+result+"判断时，"+sentence(decision)+"什么时候停，"+sentence(spoken_stop)+"反例示意，"+sentence(counter)+"换题仍检查当前题面的对象和关系，不搬上一题结论。挑战，"+sentence(m["challenge_prompt"])
            m["entry_copy"]=opening+sentence(first)+sentence(extra)+"这一步得到的"+result+"如果卡住，"+sentence(support["if_stuck"])
            m["source_alignment"]["authored_first_contact_draft"]=True
            m["static_design_review"]={
                "status":"source_bound_editorial_review",
                "source_section_ids":m["section_ids"],
                "participant_validation":"pending_real_participant_validation",
                "example_scope":"2026-10-28基础入口表达修订；保留原判据/Stop/课程绑定与语义版本，微动作和关系示意不是完整真题或真人实测。"
            }
            # No semantic/role/version/evidence migration in a copy revision.
            preserve=("method_id","brand_name","source_name","aliases","question_type","role","primary_role","secondary_roles","output_type","core_action","decision_rule","verification","stop_rule","section_ids","source_references","cases","version","status","maturity_status","practical_value","first_use_test","evaluation")
            for k in preserve:
                assert m.get(k)==previous.get(k),(mid,k)
            assert m["student_ready"] is False
            assert m["full"]["summary"]==m["core_action"]+" "+m["decision_rule"]
        new=yaml.safe_dump(document,allow_unicode=True,sort_keys=False)
        patches.append(("update",rel,(old,new)))
    lines=["*** Begin Patch"]
    for op,rel,content in patches:
        if op=="add":
            lines+=["*** Add File: "+rel]+["+"+l for l in content.splitlines()]
        else:
            old,new=content
            diff=list(difflib.unified_diff(old.splitlines(),new.splitlines(),n=3))[2:]
            lines+=["*** Update File: "+rel]+["@@" if l.startswith("@@") else l for l in diff]
    lines.append("*** End Patch")
    print("\n".join(lines))
if __name__=="__main__":
    main()
