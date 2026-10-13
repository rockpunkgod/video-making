"""Build a disposable candidate epoch; never switch live rules or evidence.

This is a mechanical staging compiler plus explicit reviewed corrections.
The result still requires semantic, student, engine and downstream acceptance.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
import yaml

from core.registry import ROOT, Registry
from scripts.capture_answer_revision import sections
from scripts.plan_answer_alignment import build_plan, TARGET

# Each tuple is one responsibility: trigger, observable action, result, stop.
# These are bounded editorial projections, not evidence of learner success.
CORRECTIONS = {
 'R03': ('题干、候选与原文有可核同义、反义或同根表达，需要核同一断言。',
  '先圈所问对象、动作与限制定位段落，再用有区分度的候选名词或动作找句；并排核完整动词关系与形副范围。',
  '产出能否等值替换的语义核对；共同对象已明示时直接比完整判断，不按对应词数量定案。',
  '仅结构相似不启动；同词、近义词命中不直接选；词义或所在句不闭合就补必要上下文，保留否定条件。'),
 'R04': ('候选有比较、最高程度或实际相对增减变化。',
  '在本题内先圈比较候选，尤其多个比较项时优先回文找真实关系，再对齐双方、属性、方向、程度、范围、阶段与条件。',
  '同一维度的等值改写可通过；确有属性、对象、阶段或强度偷换才排，产物是当前比较项核对。',
  '未找到同比较词只是未定位，不等于证伪；最高级不自动错，后来状态不补成先前性质；题内优先不改整篇题序。'),
 'R05': ('至少两个候选各有依据且原文支持同一因果链，题干方向允许比较因与果。',
  '先圈题干所问现象或具体环节；问原因就找与它相连的原因，否则画已证原因→中间结果→最终结果并对齐所问节点。',
  '只按题干核当前节点的直接作用；未明确问因时一般优先核结果是否承载所问核心信息，不是见链选最后。',
  '共同对象、先后或并列不足以启动；链或各候选缺依据即停；不把后续结果移作前一环节目的，不由排一项定另一项。'),
 'R08': ('题干问例子作用，或主旨/观点候选只复述例中细节而未概括其支持观点。',
  '圈例子及必要前后观点，分别写例中发生什么与它支持哪种判断，再核候选声称的作用或覆盖。',
  '产出例子—观点支持关系；只复述局部通常不足回答作用或主旨，抽象项也须有真实支持。',
  '直接考例中事实不用本法排细节；作用新增无依据则撤回，段首段尾和主题词只作入口，不机械见细节必排。'),
 'R10': ('所问指代或决定答案的前提，需要还原实体、状态、事件或命名概念。',
  '圈指代及所在完整谓语；实体先列可比对象并回填，状态写谁处于什么状态，概念回看它概括的行为并还原内部代词。',
  '产出有动作角色与限定支持的所指解释；有限词义分支须有明确指示解释，先核词性再比具体含义。',
  '最近名词、同数或同词性不定案；状态不缩成名词，结果不冒充原状态；附近不足按缺口扩，解释关系不明停词义分支。'),
 'R11': ('复杂句或关系妨碍看清所问主干，或候选确有同对象阶段/持续含义差异。',
  '先圈谓语及对应主体，划分真实结构并保留答题相关修饰；阶段差异核当前与目标，持续差异直接核动作含义和必要上下文。',
  '产出保留关键限制的核心关系解释；按题干取相关主旨、态度或结构观察，不要求局部题三问齐做。',
  '分结构不等于删修饰作答；不强制持续检查前先画时间线或比时长，不凭时态、持续词或转折位置定案；含义不明停该检查。'),
 'R13': ('题干有能区分所问对象或区域的名词性线索，需要找出处。',
  '圈差异名词或名词短语，回文标候选区域，再配题干实际动作与限定，没原词时查可确认近义表达。',
  '只产出待核位置；一般名词定位不受暑4特定跳读前提一概限制，也不是顺藤摸瓜的别名。',
  '同名跨段、名词无区分度或当前表达未确认就换动作线索或补证；不按次数、最近位置或同词定答案。'),
 'R14': ('已定位题的出处与实际文章推进同序，能帮助缩小当前搜索区间。',
  '标相邻已定位题的真实出处，暂估当前题可能区间，再以当前题对象和动作回文确认。',
  '只产出暂定搜索范围；题文同序是积极阅读的定位子动作，不合并为顺藤摸瓜。',
  '插叙、回叙、跨段综合、共享出处或证据落区间外时取消限制；不切死一题一段，定位不等于已答对。'),
 'R15': ('同一对象对应多个动作或关系，需要核题干所问究竟是哪一项。',
  '圈题干动词及对应主体对象，并排配回定位句的完整谓语，保留否定、阶段、范围和条件。',
  '只产出对象—动作关系解释；动作词相同仍须核施受和限制，动词定逻辑不与顺藤摸瓜合并。',
  '主体、对象或动词含义未确认不判等同；缺指代、因果或阶段联系就补必要上下文，不把一致当整项正解。'),
 'R16': ('题干问全文或段落主要内容、中心论点、主题或主要讨论对象。',
  '先圈所问全文/段落范围，扫候选共同对象并去同求异，带不同判断回该范围核贯穿内容及覆盖。',
  '产出对象—完整判断框架供候选核查；选项倒推和妖项助攻只是待验预期，正文实际内容才支持概括。',
  '局部事实、泛推理或人物品质不套主旨；不并为中心思想；共同词、较宽范围、动态词形或剩余项不定案，段意清楚不机械压全文。'),
 'R17': ('当前定位句缺决定本题的原因、结果、指代、转折或限定关系。',
  '先写清缺哪条关系，只向必要前后文扩读到能补清它的位置，再回完整断言核主体、动作和限制。',
  '产出补到的文本联系与仍存缺口；这是内部补证动作，不借左顾右盼或完形瞻前顾后的原名扩大范围。',
  '定位句已闭合即停扩读；固定邻一句仍不足就按缺口继续，材料不足或关系不明则暂留，不编依据。'),
 'F01': ('整篇七选五开头或单题开始，需要先识别选项间实际可见的结构、主角与真谓语时间差异。',
  '在选项区按句型、实际主角、真谓语时间各标一次组并说清字母；无区分度如实标记，随后按突破口回正文。',
  '只产出优先候选组；放回正文核对象、动作、两侧关系和段落任务，内容证据才定案。',
  '无区别不编组；发现漏纳、指代或谓语初筛错误可在当前比较纠正，不重演完整三分；不据组小、占用或剩一项选。'),
 'F03': ('候选的语法主语、核心话题、指代或祈使句行动者可形成相关组。',
  '开头圈主体与指代并展示暂定字母组，回文确认当前主体对象，再在同组比完整动作及段落推进。',
  '产出主体相关候选；宾语代词也可承接话题，共同主角只缩范围，不代替内容闭环。',
  '同主角但对象不同继续比；新证据改变话题或发现漏纳、指代初筛错误时更正，不重演分组；归属不明暂留。'),
 'F04': ('候选的真谓语或实际时间关系有可观察分组差异。',
  '开头圈真谓语与时间词并说字母组，回文确认局部事件阶段，再在同组比主体、动作、指代、评价与两侧内容。',
  '只产出当前时间相关候选；时间状语可作回查阶段的线索，不能以同组时间直接定案。',
  '非谓语词尾不分时态；无差异停止该维筛选；经历与感悟可切换，初筛错误可更正但不重演；不只比较异组后就选。'),
 'F05': ('段首或第一段段尾常提示统领关系，但仍需候选概括并引出实际后续展开。',
  '先标候选管一个段还是后续若干分项，概括全部管辖内容的共同对象和展开方向，再核代词承接与实际展开。',
  '产出统领范围及段落任务解释；候选既要覆盖全部管辖范围，也要能引出实际展开。',
  '位置或Here are不定案；只对应一个例子、数据或步骤就撤回初判；不把较概括项推广到任意位置，竞争未闭合继续核。'),
 'F06': ('候选与正文有可确认词语、指代或整句内容呼应，而非只是同一主题。',
  '圈呼应表达并写它承接哪个对象、事件或整句内容，回填两侧；需要时由空后代词反查候选提供的前提。',
  '产出实际呼应的核验；同词多项局部接通时比空前条件、空后结果与全段任务，不数重词定案。',
  '无明确呼应不命名本法；形式it不强找名词，latter要有真实成对对象；前提未引出不提前放，段界连下段起句核。'),
 'F10': ('整篇初填完成，需要回填并按课程排除项分析核对未选候选。',
  '逐空回填核对象、动作、两侧功能与段落任务，再核未选项的内容承接和断言范围，疑似对应已填位置则返回。',
  '产出已填关系的核验和待回查位置；不要求学生逐项重演全部分组与无关排除过程。',
  '内容仍多项成立或缺关键关系就暂留；占用与剩余不作本空依据，已证伪项不无据恢复。'),
 'F11': ('当前空有需要解决的竞争候选，且能用本空条件、结果及段落任务核差异。',
  '并排核竞争项完整断言怎样承接空前具体条件、空后结果与全段问题，标实际支持或冲突。',
  '本空决定性内容关系闭合才定案；同形式、同词或时间只给候选入口。',
  '多个候选仍成立则暂留，不按主观更像原因撤销另一项；不靠他空占用、剩一项或无文本的直觉定案。'),
 'C02': ('当前空要核前后提示，近处不足才需更远上下文。',
  '圈两侧对象、动作、评价、时间及候选额外前提；近处够则回填，不够写缺口并向真实复现、回答、结果或评价扩。',
  '产出线索与候选的实际联系和回填核验；多个线索一并核，不只截支持初选的一处。',
  '仍不足就暂留，找到独立提示后返回，不强制原空号；相邻待定空、已占项或先报答案不互证。'),
 'C03': ('需要先建立粗框架，或当前空确实依赖主题、基调、视角或局部线索不足。',
  '从首句或前几句标人物、背景、主题、视角与暂定基调，再核当前空实际需要的对象和关系。',
  '产出粗框架而非答案；首句提供理解前提，单空已局部闭合不必每次复述。',
  '首句未给的信息不预编；积极态度不等于遭遇顺利，外在表现、遭遇与态度不混同；不报课程系列为方法。'),
 'C04': ('空内词的句法作用能指向当前需要的修饰或动作线索。',
  '标空内作用并圈实际修饰同一对象或动作的结构；动词空核谁做、指向谁及真实施受归属。',
  '只产出可查线索位置；同词性、形式或后缀不定答案，观察者感受不能移作人物行动。',
  '修饰对象、逻辑主语或具体词义未确认先停该定位结论；不凭职业惯例、心理猜测补候选所需前提。'),
 'C07': ('名词空有可确认原词、近义、同源复现或真实语义对照线索。',
  '圈相关表达及其内容，确认仍指同一人物、状态或事件；已知派生关系再核词义，必要时向后找并回填。',
  '只产出词汇呼应的对象线索；对照需同一语义维度，后续仍核句意、推进和主线。',
  '未知词根不拆猜，共同后缀或形近不当同根；and不强定同向，复现、类别或次数不定案；同指或词义不明暂留。'),
 'A03': ('要点已确定，但还写不出准确的基础句。',
  '先写核心主体，再写动作或状态，最后加入题面支持且服务要点的时间地点等细节。',
  '产出可继续组篇的准确基础句；主干、搭配、时态与题面要点对应，不代表整篇任务完成。',
  '主体或动作不明先回要点，不编背景；基础不成立先修，不靠堆修饰升级，基础句式锚定不与另两种方法合并。'),
 'A04': ('已有准确主干及相关动作，需要按真实逻辑合成复杂表达。',
  '各动作先独立写成正确简单句，标实际关系，再选合适从句、非谓语、连接词或介词短语粘连。',
  '产出主干、指代与原关系不变的复杂句块；两简一复从是原课扩句练习，不是整篇句数或从句配额。',
  '基础句或关系未成立不合并；动作主体或依附错误退回独立句，不为复杂度强拼或把训练配比作语法上限。'),
 'A05': ('中文信息与修饰混杂，需要重构英文表达而非按整篇词数选法。',
  '拆核心与修饰信息，按主体→核心动作→场景重组，再校时态、词性、单复数和衔接风格。',
  '产出保留原义、对象与限制的句子；按信息复杂度与表达能力选用，不由110/120整篇词数触发。',
  '核心不清先停重排；否定、时间、数量、条件不能当枝叶删；不宣称缺连续口述或新完整例的分支已全面验收。'),
 'A08': ('应用文题面需要安排文体、对象与交际目的相符的内容骨架。',
  '圈题面文体、对象、目的及明示格式，让各段承担实际要点功能，再选择相应文体骨架。',
  '产出服务题面内容的结构计划；人物介绍等细化依题目取用，三件套四件套等整理便称不冒充独立原名。',
  '题面已给标题首尾或特殊格式就按要求保留，不硬套段数；示范句型不作每篇配额，骨架齐不等于要点完成。'),
 'A10': ('课后需要按当前表达缺口安排下一项写作训练。',
  '依据现有稿件或练习，标任务骨架、基础翻译、素材调用或自然升级的缺口，选择一个对应阶段的复练动作。',
  '产出下一次具体训练计划；读背仿与分数锚定只作原课程训练参考，不是现场答案或个体得分保证。',
  '没有现稿不精确承诺档次；基础未稳不跳华丽结构，金句积累数量不作单篇使用数，110/120不当整篇词数策略。'),
 'W01': ('原文与两段开头语齐备，需要构思受原文约束的续写框架。',
  '先读两首句提出待证问题，再回原文找人物矛盾与时空；依跳定思提润留下线索、冲突主题、构思、功能提纲与润色检查。',
  '产出可写框架；润检查结局怎样回应伏笔或关键词，感悟如有须由情节推出，不证明唯一剧情或分数。',
  '缺必要材料只校现有语言；人物、事实或衔接不成立先修，不能借独立升华句补框架，也不混同各版五步成文原名。'),
 'W04': ('两段首句的状态、人物或任务留下需要回原文取证的缺口。',
  '圈首句已明示的人事物、状态、时地和任务，带状态变化的问题回原文，再标段间确有必要的过程。',
  '产出取证位置和待补缺口；核首句元素与续文的实际必要联系，不让每个人物或名词固定占一句。',
  '缺首句或前提不足停完整反推；可省过渡不强加，已衔接不重述下一段进行中事件，不凭名词补唯一剧情。'),
 'W06': ('续写不知从哪里下笔，需要从原文抓核心人物、矛盾与关键线索。',
  '给这三项各圈真实原文位置，写谁因何受阻、哪条线索约束后续。',
  '产出构思入口；三要素是分档训练中的取证动作，不自动证明解决情节。',
  '原文找不到就留缺口，不编主角或事故补齐三点；不把段首句加动作加结局的练习比例当全体写作配额。'),
 'W07': ('拟写关键行为或结果需要核是否回应原文的重要线索。',
  '将关键行为、物件结果与原文重要伏笔连线，写清动机、用途或后果，标未兑现的重要联系。',
  '产出伏笔回应核验；按当前故事与两首句选择必要元素，不要求每个物件都出现。',
  '只有同词而无真实联系就停确认；不为了兑现添无铺垫能力、事故或人物，缺原文不证明回扣。'),
 'W08': ('事件跳跃，需要补清本题实际人物动机与行动结果的因果桥。',
  '写因为A→行动B→结果C，为每条边标原文条件或合理铺垫，逐条说明怎样促成下一步。',
  '产出可核因果链；先后不自动等于因果，拟写发展须受人物能力和原文事实约束。',
  '边上只有猜测互证或物理条件不成立就停推进，先补合理动机/行动，不靠再添结果证明前一步。'),
 'W09': ('主线与衔接已成立，但有效动作或画面细节不足。',
  '在推进主线的行动旁选有用的动作、神态或环境细节，注明它显示的状态或推进的环节。',
  '产出服务情节的细节扩写；每段选少量有效位置，训练的数量不作评分硬项。',
  '框架未成立先修；只凑字数不加。春11环境素材位置建议仅限该组模板，不扩大成所有环境描写禁令或强制句位。'),
 'W10': ('相邻句对象与行动衔接不清，或机械堆连接词影响表达。',
  '圈共同对象和代词回指，回填所指并核动作接续；可用关键词复现或指代替代无用连接词。',
  '产出对象、动作与关系连贯的表达；必要因果、否定和转折须保留。',
  '代词歧义先明确对象；同对象不证明有因果，删词会改关系就保留或换准确表达，不为无痕而删逻辑。'),
 'W11': ('原文核心矛盾已有轨道，解决过程确实适合加入有铺垫小波折。',
  '从当前矛盾找合理小障碍，写触发条件与解决行动，再核人物能力和主线不变。',
  '产出受原文约束的过程扩展；节外生枝原字与合理波折要求并存，不解释为凭空添事故。',
  '无铺垫或框架未完整先停；不加无据关键人物、超能力或事故，每篇不强制转折，正向不等于大团圆。'),
 'W12': ('基础意思与句法已准确，需要让当前场景的词更具体得体。',
  '圈笼统词，写清此处实际动作或状态，再选对象、力度与搭配匹配的词并回填。',
  '产出保原义、搭配自然的替换；场景化高级词是素材，不按原示范固定词对迁移。',
  '基础未准确先修，生词的力度或搭配不明保留准确常用词；不从词表盲抄或按替换数量评分。'),
 'W13': ('结局需要核是否自然回应原文关键细节、核心矛盾或人物变化。',
  '把解决结果对应回原文关键线索，指出行动或感悟怎样带出本题主题。',
  '产出主题回应核验；素材分类与积累数量不作每篇必写的独立升华句。',
  '核心矛盾未解先停喊道理；抽象主题不能换成本题内容就撤回，没独立升华句不自动降档或判重大缺失。'),
 'W14': ('功能提纲已确定，需要分清哪里保证衔接、哪里适合扩写。',
  '标接首句、必要桥接、解决与收束等实际功能为骨架，其余位置按本题因果与画面需要选写有把握内容。',
  '产出骨架与扩写分工；采用十句时可对应功能位，但不是所有题固定句数。',
  '骨架未接通先补功能；非功能位也受原文约束，不会什么就硬背什么，不因句数或句位本身扣分。'),
 'W16': ('已有续写稿，需要依据真实缺口安排下一次训练。',
  '按现稿先核完整和因果，再选细节衔接、合理转折或精准表达中的一项复练。',
  '产出可执行训练任务；秋16分档训练与25分整体评分分别使用，不拼成官方逐项配额。',
  '缺现稿不精确诊断或承诺升档；基础未稳不跳华丽升级，不机械增加动作、复杂句、转折或独立升华句。'),
 'R02': ('原文和候选在主体、施受、愿望/事实或能力/意愿上有可比差异。',
  '并排圈主体与完整谓语；按本题差异核谁对谁做什么，或希望/事实、能力/意愿，不强制三格串行。',
  '只有确认主体、施受或谓语状态被无依据偷换才排除；一致只通过这一核查。',
  '没有可比差异就不用；题干已明示共同对象时不因候选省略主体排除，不能据剩余项定案。'),
 'R06': ('主旨、标题或目的候选疑似遗漏已经核实的核心对象、动作或关系。',
  '把候选拆成谈什么与作什么判断，对照所问范围的已证核心关系，指出具体遗漏。',
  '确认遗漏所问核心内容才排该项；诊断标签不负责生成全文框架，也不独立完成整题。',
  '没有已证核心关系先停；省略、近义或上位概念能覆盖时，不能因没原词判缺失。'),
 'R09': ('主要段落齐备，需要全文主题、态度、结构、标题或长文框架。',
  '先读实际题干及相关选项；共同/重复概念仅作假设；再化简有效首尾，最后读中间段首及必要回答或段尾。',
  '回全文验证对象、核心判断、结构任务三格，产出全文骨架卡，不直接定答案。',
  '局部题或缺主要段落不启动；重复线索缺失只跳过该观察；三格无正文支持则暂留，不编相关题目。'),
 'R12': ('需要由题面找对应段落、事件或信息区；暑4跳读版本还需主题明确且多个题目有主旨限定。',
  '圈实际题干所问对象和范围，以当前有区分力的专名、数字或其他标志标候选区域。',
  '产出待核位置；再交给完整对象、动作与限定核验，定位不报答案。',
  '暑4版本前提不成立，不借一般定位放宽；标签无区分度或位置不闭合就换线索或扩证，不假设一题一段。'),
 'C01': ('当前空的词义、关系或搭配不能在孤立空位闭合。',
  '标空位角色，圈最近对象/动作提示；最近不足才向真实复现、回答、结果或评价扩读，再回填核具体语义与联系。',
  '产出当前空的线索路径，标已补清和仍缺的关系；内部框架不独立定案。',
  '当前空的决定性词义或关系仍不明就暂留；找到独立提示再返回，不强制原空号、两遍或三遍。'),
 'A02': ('有应用文题目，需要从要点安排到成稿的通用训练支架。',
  '圈题面限定与全部要点，搭合适文体骨架，写准确单句再按真实关系组篇、升级和复核。',
  '产出有要点和复核记录的成稿计划；六步是通用梳理框架，不冒充独立课程原名算法。',
  '题目或对象不清先补材料；基础内容未成立先修，不照抄不合语境模板，不保证分数。'),
 'A06': ('课后要独立调用表达，原中文与对照范文可用。',
  '中文必要时先简化，再独立英译、对照范文、记录并背诵缺失词或句式；第五步AI升级可选。',
  '产出自己的表达缺口与已核素材；准确异写可保留，AI建议须保原意且搭配成立。',
  '范文或AI改变任务、意思或搭配未核就不背不抄；挖空法另列，不塞入寒4五步或改称六步。'),
 'A07': ('基础句准确，已有相关简单句需要按真实逻辑粘连。',
  '并排写出相关简单句，标共同主体和实际关系，再选合适从句、非谓语或介词短语拼接。',
  '合成句须保原信息、主体、关系和句法；口诀只是记忆称呼，不规定拆字步骤或固定先后。',
  '主体、语义关系或搭配不成立退回独立句；不靠110/120整篇词数选法，不借续写同名定义。'),
 'W02': ('两段开头语和原文齐全，需要检查实际自写内容的功能衔接。',
  '先标自写两段开头、第一段末、结局与收束五个功能位；采用自写十句时才对应1/5/6/9/10。',
  '按真实位置核接首句、必要段间桥接、冲突解决和主题回应；产出功能缺口，不按编号评分。',
  '句数不同按现稿映射，不凑十句；给定首句不要求重抄；已衔接就不重述或补可省过渡。'),
 'W03': ('原文及两段首句齐备，需要按一个明确来源版本整理已知与未知情节槽。',
  '先注明版本：寒8板书P目的/T方式/S苦难/D结局；同课表格P需求/T方法/S困难/D结局；逐槽填首句已知与原文约束。',
  '产出该版本的已知/未知情节槽；寒14需求/波折/方案/结局及其分析表另留，旧高二PPT也不混用。',
  '未注明版本先停；未知槽留空，不凭口诀补事故或救场者；Needs/Difficulties/Solutions/Denouement不是PTSD英文展开。'),
 'W05': ('主线已有成立行动，但该行动太笼统而需要具体连贯描写。',
  '圈已有核心行动，拆真实相连的小动作，标人物、先后和因果，再补合语境状态。',
  '产出受原文约束的动作链；两动作/三动作是微型示范，不是全体句子上限或评分配额。',
  '没有成立行动不拆；人物能力、物理条件或因果不成立则撤回；动作面独立定义未核，不补成动作加心理加环境。'),
 'W15': ('原文、两段首句和完整自写续文齐备，且请求评分。',
  '按25分档次逐项引用原文与自写稿证据，先核融洽、情节和完整性，再核语言与衔接。',
  '产出有证据的档次建议；训练的动作数、句型数、十句位置和独立升华句不作硬扣分项。',
  '缺必要材料不报完整分；不抄给定首句正常；仅原手写可见且影响交际才按规范处理书写，不伪造固定扣分。'),
}

SOURCE_NAMES = {
 'R06':('主旨缺失（判项诊断用语）','internal_rule'),
 'R12':('跳读定位','method'), 'R13':('名词定出处','sub_action'),
 'R14':('题文同序','sub_action'), 'R15':('动词定逻辑','sub_action'),
 'R16':('mainly题与主旨大意','framework'),
 'R17':('定位后必要上下文核对（内部动作说明）','verification_rule'),
 'C01':('语篇行文结构（内部梳理框架）','framework'),
 'C03':('首句建立粗框架（语篇行文结构的子动作）','sub_action'),
 'A02':('应用文写作六步训练法通用梳理框架','framework'),
 'A03':('基础句式锚定法','method'), 'A04':('复杂句式模块法','method'),
 'A05':('长句翻译重构法','method'), 'A06':('富兰克林写作法（寒4五步）','framework'),
 'W05':('动作链','method'),
}

# Authored first-contact copies for the six priority entries. These are static
# drafts, not measured speaking times, First-use tests or Practicality passes.
FIRST_CONTACT = {
 'R01': {
  '10s':'两项都像原文？把多说的那项拆成A+B，只查B；无直接或间接依据才排。',
  '30s':'前半句能对上，后半句却多了目的、范围或时间？先圈原文已支持的A，再圈新增B。比如只说参加，却多说为了获奖，就回文查获奖目的。B有合理文本支持就停止排除；没原词不等于没依据。',
  '90s':'候选核心与原文对应，却可能新增人物、目的、时间、范围、因果或确定程度时，先圈A与B，只为B找直接陈述或必要上下文的间接支持。确认无支持或矛盾才排该项，排一项不证明剩余项正确。反例：原文事实与数量关系已支持概括，候选没逐字复述也不能排。换题仍先对齐核心，再核新增限制。挑战：先不选，只圈候选多说了什么，并标去哪里查。',
  'stop':'共同核心A未确认时不强拆；B有直接或间接支持时停止排除，不能因没原词判错；排除后仍核保留项。',
 },
 'R02': {
  '10s':'词都相同还犹豫？圈主体和完整谓语，只核偷换处：谁对谁、想与做、能与愿；一致不等于答案。',
  '30s':'两句人物与动词都像，可能把希望写成已经做到？并排圈主体和完整谓语，只查当前差异。比如希望帮助，不等于已经帮助；若是施受差异再画X→动作→Y。没有偷换就停本法，别由一致宣布整项正确。',
  '90s':'看到主体、施受、愿望与事实或能力与意愿的可比差异才启动。先并排圈谁及完整谓语，保留希望、能够、已经等状态；按当前差异核人物归属或画动作箭头，不强制每题走同一三格。只有文本确认偷换才排；通过本检查仍要核其他限制。反例：题干已给共同主体，候选省略姓名并非换主体。换题仍保完整谓语，不搬上一题人物关系。挑战：先不选，指出本题是哪种差异，再圈被换的一处。',
 },
 'R06': {
  '10s':'主旨项看着相关？对照已证核心，说清少了哪个对象或关系；概括能覆盖，别因没原词排。',
  '30s':'全文框架已核好，主旨候选却只说其中一部分？把候选拆成对象和判断，对照已证核心。比如全文讲问题及解决，候选只讲问题，就核是否真的遗漏解决关系。省略、近义或上位概念已覆盖时停；这是缺块诊断，不是独立整题算法。',
  '90s':'主旨、标题或目的候选可能遗漏已核实核心时启动，不从选项编文章骨架。先拆候选谈什么、说什么，再指出它具体遗漏哪个对象、动作或关系，并在所问范围标证据。确认遗漏才排该项；有更多词或更大范围不自动正确。反例：候选用上位概念完整覆盖全文，没重复每个原词也不能判缺块。核心尚未核实就先建框架；材料不足则停。换题仍检查实际覆盖，不固定A+B+C块数。挑战：先不选，只指出疑似遗漏及能证明它重要的文本位置。',
 },
 'R09': {
  '10s':'长文一团乱？先看题干与相关选项，再核正文，压出对象、判断、结构；骨架不是答案。',
  '30s':'全文主题、态度、标题或框架任务卡住时，先读实际题干与相关选项，共同概念只作假设；再核有效首尾、中间段首及必要展开。比如首段只讲背景就不能当核心判断。压成对象、判断、结构三格；缺主要段落停，没重复词则跳过该线索。',
  '90s':'主要段落齐备且需要全文框架才启动。第一眼看题面实际题干与相关选项，没有主旨题就不编主旨选项。共同或重复概念可形成假设；再化简有效首尾，再看中间段首，背景段首转看必要段尾，设问连回答。最后用全文核对象、核心判断、结构任务三格，唯一产物是全文骨架卡。反例：背景词反复出现，真正判断却在后文；词频和首尾位置都不能直接定案。缺主要段落或三格无法核实则停，重复线索缺失只跳过该观察。换题仍按实际任务取证而非搬文章结构。挑战：先标第一眼读的位置，再填三格并逐格指出证据。',
 },
 'F01': {
  '10s':'七项乱试？先按句型、主角、时间分组并说字母，再回正文。分组不定案。',
  '30s':'七选五开始别逐项乱填。扫A–G，按完整句型、实际主角和真谓语时间各分一次，说清字母；没有差异的维度如实跳过。比如同为祈使句仍可能讲不同对象，须回空前空后比内容。发现初筛错误可更正，不重演分组；内容不闭合就暂留。',
  '90s':'整篇开头统一三分一次，单题在该题开头做；结构、主角或真谓语时间有差异才形成有用组。第一刀先在选项区标实际组别并说清A–G字母，无区分度不编组，再按突破口回正文核对象、动作、两侧关系和段落任务。只得优先候选组，不直接得答案。反例：过去事件之后转为一般感悟，不能只留过去时项；同组两项也可能只一项接通内容。新证据纠正初筛时在当前比较说明，不再展示完整分组。换题仍由新选项分组，不搬旧组。挑战：先不填空，只按主角分A–G，指出一个无区分度的维度与待正文核的关系。',
  'stop':'三分完成即转正文；新证据可纠正初筛但不重演完整分组；维度无差异不强分，内容不闭合就暂留，不据占用或剩一项定案。',
 },
 'G01': {
  '10s':'看到空先别变词。先标有无提示词，再问位置要什么；确认要动词，才分谓语与非谓语。',
  '30s':'括号里的词先别变。标有无提示词，再圈未填句里决定空位功能的限定、修饰、连接或主干。比如environmental ___ (protect)需要名词中心，不因提示词是动词就走动词路。无提示词进功能词；到节点后停总路线，用该节点句法、搭配与句意求证。',
  '90s':'任何语法空开始时先在未填句取证。先标有无提示词，再圈分句主干、标点及空前后的支配或修饰关系：无提示词去功能词节点，有提示词先判名、形、副、代、数或动；确认需动词才分谓语/非谓语。产物只是知识节点，不是答案。反例：提示protect但位置要名词；介词后需要名词性成分也不必一律派生名词，doing可有相应功能。句法功能不明先补完整句，到节点就改用具体规则，再回填核搭配与句意。换题仍判新位置，不背提示词变形套路。挑战：不填词，只标有无提示词、空位功能、决定它的词与下一节点。',
  'stop':'空位功能或必要句子未确认时先停；到达知识节点即停止总路线，改用节点句法、搭配与句意核验，不把路由当答案。',
 },
}

# Reconcile auxiliary entry fields too; updating only core_action would leave
# the old algorithm in formulas, challenges and transfer instructions.
ENTRY_CORRECTIONS = {
 'R02': {
  'visual_formula':'原文 ↔ 候选：主体 + 完整谓语\n只核本题差异\n谁→动作→谁 / 希望≠事实 / 能力≠意愿\n证实偷换→排；一致→仅过本项',
  'memory_line':'圈谁与完整谓语，只核当前偷换处。',
  'challenge_prompt':'先不选，指出本题是主体、施受、愿望/事实还是能力/意愿差异，再圈具体被换的一处。',
 },
 'R06': {
  'visual_formula':'已证所问核心：对象 + 关系\n候选：谈什么 + 判断什么\n确认遗漏核心 → 排该项\n近义/省略已覆盖 → 不判缺失',
  'memory_line':'核心先有证据，才说这项缺什么。',
  'challenge_prompt':'先不选，只指出候选疑似遗漏什么，并标能证明它是所问核心的文本位置。',
  'transfer_pattern':'换全文或段落概括任务，仍先核所问范围的实际核心，再诊断具体遗漏，不固定块数。',
  'counterexamples':['候选用省略、近义或上位概念准确覆盖所问核心，没重复每个原词也不能判缺失。'],
 },
 'R09': {
  'visual_formula':'题面实际题干 + 相关选项\n→ 可用共同概念（假设，可跳过）\n→ 有效首尾 → 中间段首及必要展开\n→ 全文核验\n骨架卡：对象 | 核心判断 | 结构任务',
  'memory_line':'先按题面取证，再压出对象、判断、结构。',
  'challenge_prompt':'先标第一眼应读的实际题干与相关选项，再填对象、核心判断和结构任务三格，逐格指出正文证据。',
 },
 'A06': {
  'visual_formula':'必要时简化中文 → 独立英译\n→ 对照范文 → 记背缺失表达\n→ 可选AI升级（核原义与搭配）\n挖空法：另列，不塞进五步',
  'memory_line':'先自己译，对照后记缺口；AI升级可选。',
  'transfer_pattern':'换范文仍先独立产出再对照，只记录已核准表达；仿写和挖空可另练，不改寒4五步定义。',
 },
 'A07': {
  'visual_formula':'相关正确简单句\n→ 标主体 + 真实关系\n→ 从句 / 非谓语 / 介词短语（按需选）\n→ 核原义与句法，不拆口诀排步骤',
  'memory_line':'把相关简单句按真实关系粘起来。',
  'challenge_prompt':'先并排写两句准确简单句，只标真实关系，再选一种合适粘连方式并说明主体是否保持。',
  'transfer_pattern':'换题仍从当前准确句与真实关系选择粘连，不固定层层升级、词数门槛或口诀顺序。',
 },
 'W02': {
  'visual_formula':'实际自写位置 → 接首句 / 搭桥 / 接第二首句 / 解决 / 回应\n采用十句 → 可映射1/5/6/9/10\n句数不同 → 仍查功能，不凑数\n给定首句不必重抄',
  'memory_line':'先查五个功能，十句只是可选句位。',
  'challenge_prompt':'先不写全文，在实际提纲上标五个功能位置；若选十句框架，再对应1/5/6/9/10，指出哪座桥确实必要。',
 },
 'W03': {
  'visual_formula':'先选来源版本（不混定义）\n寒8板书：目的 | 方式 | 苦难 | 结局\n同课表格：需求 | 方法 | 困难 | 结局\n寒14、旧PPT：各自另列\n每格↔首句/原文；未知→留空',
  'memory_line':'先说用哪版，再填已知，未知先留空。',
  'challenge_prompt':'先注明一个来源版本，不写故事；逐槽标两首句已知与原文约束，未知处留空，并指出另一版哪两个槽不能混用。',
  'transfer_pattern':'换故事仍选清来源版本，再由新原文和两首句约束本版槽位，不迁移旧题困难或解决者。',
  'counterexamples':['把寒8的T方式与寒14的T波折当同一职责，或把分析表四个英文词当PTSD展开，都不能混用；填满也不证明情节有依据。'],
 },
 'W05': {
  'visual_formula':'已有成立行动\n→ 所需相连小动作（不凑数）\n→ 核人物能力 / 先后 / 因果 / 状态\n动作面：独立定义待核',
  'memory_line':'拆出必要小动作，不凑三个、不补能力。',
  'challenge_prompt':'先不堆修饰，把一个已有行动拆成所需小动作，为每步标主体、先后和依据；若不需拆就说明理由。',
 },
 'W09': {
  'counterexamples':['原场景需要一处有效环境细节，不因落在功能位或结尾就一概拒绝；春11某组环境模板的位置建议不能泛化为所有描写禁令。'],
 },
}

FIRST_CUTS = {
 'R02':'并排圈原文与候选的主体和完整谓语，标这题实际在比哪种差异。',
 'R06':'圈候选谈的对象和作出的判断，旁边写已核实的所问核心。',
 'R09':'先圈实际题干所问范围，再读题面真正给出的相关选项；没有就不编。',
 'F01':'先在A–G选项区标结构、主角、真谓语时间的暂定字母组，不填空。',
 'C01':'在当前空旁标要查词义、关系还是搭配，再圈最近的对象或动作提示。',
}


def corrected_card(original):
    m=deepcopy(original); mid=m['method_id']
    if mid in SOURCE_NAMES:
        m['source_name'],m['method_type']=SOURCE_NAMES[mid]
        m['aliases']=[m['source_name']]
    m.update(deepcopy(ENTRY_CORRECTIONS.get(mid,{})))
    if mid not in CORRECTIONS:
        if mid in FIRST_CONTACT:
            copy=FIRST_CONTACT[mid]
            m['compact'].update({k:copy[k] for k in ('10s','30s','90s')})
            m['stop_rule']=copy['stop']; m['four_step_card']['stop']=copy['stop']
            m['practicality_gate']['stop']=copy['stop']; m['student_ready']=False
            m['entry_copy']=copy['90s']
        return m
    trigger,action,judge,stop=CORRECTIONS[mid]
    m.update(trigger_cues=[trigger],core_action=action,decision_rule=judge,stop_rule=stop)
    m['four_step_card']={'start':trigger,'first_cut':FIRST_CUTS.get(mid,action),'judge':judge,'stop':stop}
    m['practicality_gate'].update(trigger=trigger,action=action,
                                  output=m['output_type']+'；'+judge,stop=stop,
                                  status='design_complete_empirical_pending')
    m['verification']=judge+' '+stop
    m['entry_copy']=trigger+' 手上先做：'+action+' 做完得到：'+judge+' 停止：'+stop
    # A full correction is staged first. Short-form teaching is NOT declared
    # ready merely because a templated projection can concatenate its fields.
    m['student_ready']=False
    m['compact']={'line':action,'boundary':stop,
                  '10s':action+' '+judge,
                  '30s':trigger+' '+action+' '+stop,
                  '90s':m['entry_copy']+' 反例（边界示意，非真题）：'+'；'.join(m['counterexamples'])+
                         ' 挑战：'+m['challenge_prompt']}
    m['failure_cases']=[m['common_wrong_instinct'],stop]
    if mid in FIRST_CONTACT:
        m['compact'].update({k:FIRST_CONTACT[mid][k] for k in ('10s','30s','90s')})
    m['memory_line']=ENTRY_CORRECTIONS.get(mid,{}).get('memory_line',action)
    m['practicality_gate']['transfer']=m['transfer_pattern']
    if mid in FIRST_CONTACT:
        m['entry_copy']=m['compact']['10s']+'\n\n'+m['compact']['90s']
    return m


def stage(parent=None):
    plan=build_plan(); live=Registry(snapshot_commit=plan['from_commit'])
    parent=Path(parent or ROOT/'local-data/answer-alignment-2026-10-13')
    parent.mkdir(parents=True,exist_ok=True)
    target=Path(tempfile.mkdtemp(prefix='candidate-61bc9c3-',dir=parent))
    source=ROOT/'provenance/upstream-revisions'/TARGET/'files'
    def save(path,value):
        dest=target/path; dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(yaml.safe_dump(value,allow_unicode=True,sort_keys=False),encoding='utf-8')
    for directory in ('schemas','cases'):
        shutil.copytree(ROOT/directory,target/directory)
    # Preserve provenance instead of changing a source citation to the new
    # commit. These copied examples remain old-epoch evidence until re-reviewed.
    for relative,case in live.case_inventory().items():
        case['method_version']=live.methods[case['method_id']]['version']
        case['source_commit']=live.index['source_baseline']['commit']
        save(relative,case)
    baseline=live._load('provenance/manifest.yaml')
    manifest={'repository':baseline['repository'],'commit':TARGET,'files':[]}
    section_index={}; documents=[]; lookup={}
    for row in baseline['files']:
        relative=row['path']; raw=(source/relative).read_bytes()
        dest=target/'provenance/ANSWER'/relative
        dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(raw)
        manifest['files'].append({'path':relative,'sha256':hashlib.sha256(raw).hexdigest()})
        if Path(relative).suffix!='.md': continue
        ids=[]
        for s in sections(raw.decode('utf-8')):
            sid=hashlib.sha256(f"{relative}:{s['line_start']-1}".encode()).hexdigest()[:16]
            section_index[sid]={'path':relative,**s,'commit':TARGET}; ids.append(sid)
            lookup[(relative,s['heading'])]=sid
        documents.append({'path':relative,'sha256':hashlib.sha256(raw).hexdigest(),'sections':ids})
    def new_ids(binding):
        return [lookup[(x['path'],x['heading'])] for x in binding['targets']]
    relocation={b['old_section_id']:new_ids(b) for row in plan['methods'] for b in row['bindings']}
    def rebind(sids):
        result=[]
        for sid in sids:
            if sid in relocation: current=relocation[sid]
            else:
                old=live.sources['sections'][sid]; current=[lookup[(old['path'],old['heading'])]]
            result.extend(x for x in current if x not in result)
        return result
    index=deepcopy(live.index)
    index['source_baseline'].update(commit=TARGET,captured_at='2026-10-13')
    index['cloze_order_policy']='evidence_driven_visits'
    index['cloze_order_source']={'path':'gaokao-english/references/delivery-contract.md',
                                 'heading':'做题顺序','commit':TARGET,
                                 'quote':'完形不强制固定空号顺序、两遍作答或先易后难'}
    index['course_identities']=plan['course_identities']
    plan_by_id={m['method_id']:m for m in plan['methods']}
    pending=[]
    for path in index['method_files']:
        module=live._load(path)
        for i,old in enumerate(module['methods']):
            m=corrected_card(old); mid=m['method_id']; row=plan_by_id[mid]
            parts=m['version'].split('.'); parts[1]=str(int(parts[1])+1); parts[2]='0'
            m['version']='.'.join(parts); m['section_ids']=rebind(old['section_ids'])
            m['source_references']=[{'repository':manifest['repository'],**{k:s[k] for k in ('path','heading','commit')}}
                                     for s in row['resolved_references']]
            # full is also transported to downstream consumers. Do not leave
            # old summaries, source IDs or fixed-order rules hidden there.
            m['full']=deepcopy(old['full'])
            m['full'].update(summary=m['core_action']+' '+m['decision_rule'],
                             source_boundary=m['stop_rule'],
                             boundaries=[m['stop_rule'],*m['counterexamples']],
                             section_ids=list(m['section_ids']))
            if m.get('static_design_review'):
                m['static_design_review']['source_section_ids']=m['section_ids']
                m['static_design_review']['status']='source_rebound_semantic_reacceptance_pending'
            m['change_reason']='ANSWER '+TARGET+' 来源重绑定；旧证据仅按归档版本复核，新规则与传播入口仍待重新验收。'
            m['regression_result']='pending_current_epoch_semantic_and_student_acceptance'
            m['source_alignment']={'commit':TARGET,'state':'staged_not_live',
                                   'source_content_changed':row['source_content_changed'],
                                   'correction_profile_applied':mid in CORRECTIONS,
                                   'authored_first_contact_draft':mid in FIRST_CONTACT,
                                   'new_course_branches':'preserved_in_full_contract_not_automatically_aliased',
                                   'acceptance':'pending_not_inferred_from_source_or_program_tests'}
            # A source change invalidates the previous static student entry
            # until its short forms are reconciled. Do not keep a ready flag
            # just because the old prose remains syntactically well formed.
            if row['source_content_changed'] or mid in CORRECTIONS or mid in FIRST_CONTACT:
                m['student_ready']=False
                pending.append(mid)
            index['methods'][mid].update(version=m['version'])
            module['methods'][i]=m
        save(path,module)
    risks=deepcopy(live.risks)
    risks=[r for r in risks if r['risk_id'] not in plan['retired_current_risks']]
    for risk in risks:
        if risk.get('section_id'): risk['section_id']=rebind([risk['section_id']])[0]
        if risk['risk_id']=='CONTINUATION-VERSION-TENSION':
            risk['action']='逐一保留寒8板书、同课表格、寒14与旧高二PPT的定义，不混用；训练安排不作评分硬项。'
    grammar=deepcopy(live.grammar_tree); grammar['source_sections']=rebind(grammar['source_sections'])
    anti=live._load('method-registry/anti-rules.yaml')
    for rule in anti['rules']: rule['source_evidence']=rebind(rule['source_evidence'])
    save('method-registry/source-risks.yaml',{'risks':risks})
    save('method-registry/grammar-tree.yaml',grammar)
    save('method-registry/anti-rules.yaml',anti)
    save('method-registry/symptom-cues.yaml',{'routes':live.symptom_cues})
    save('method-registry/source-sections.yaml',{'sections':section_index,'documents':documents})
    save('method-registry/registry.yaml',index); save('provenance/manifest.yaml',manifest)
    with patch('core.registry.ROOT',target):
        candidate=Registry(); validation=candidate.validate()
    from scripts.generate_assets import generate
    projections=generate(registry=candidate,output_root=target)
    generate(check=True,registry=candidate,output_root=target)
    report={'scope':'disposable_candidate_epoch_only','path':str(target),'from_commit':plan['from_commit'],
            'to_commit':TARGET,'runtime_switched':False,'source_and_schema_validation':validation,
            'generated_candidate_projections':projections,
            'corrected_profiles':list(CORRECTIONS),'student_short_form_drafts':list(FIRST_CONTACT),
            'student_short_form_review_required':pending,
            'semantic_acceptance':'pending','student_acceptance':'pending','downstream_refresh':'pending',
            'real_evidence_mutated':False,'release_promotion_applied':False}
    (target/'stage-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(stage(),ensure_ascii=False,indent=2))
