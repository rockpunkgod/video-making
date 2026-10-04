"""One-time, source-pinned mechanical migration; never imports internet teaching facts."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'provenance/ANSWER'
COMMIT = 'b04ebc26d7fa096404111a0bb12f6c77cc8525b9'
MODULES = {
    'reading': ('阅读理解', 'gaokao-english/references/reading-comprehension.md'),
    'seven-five': ('七选五', 'gaokao-english/references/seven-five.md'),
    'cloze': ('完形填空', 'gaokao-english/references/cloze.md'),
    'grammar': ('语法填空', 'gaokao-grammar-fill/references/grammar-fill.md'),
    'application-writing': ('应用文', 'gaokao-writing/references/application-writing-and-correction.md'),
    'continuation-writing': ('读后续写', 'gaokao-writing/references/continuation-writing-and-correction.md'),
}

def save(path, obj):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), encoding='utf-8')

def text(path, content):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')

def import_sections():
    sections = {}
    coverage = []
    for p in sorted(SOURCE.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(SOURCE).as_posix()
        if p.suffix != '.md':
            continue
        raw = p.read_text(encoding='utf-8')
        lines = raw.splitlines(keepends=True)
        starts = [0] + [i for i, line in enumerate(lines) if i > 0 and re.match(r'#{2,3} ', line)] + [len(lines)]
        ids = []
        for a, b in zip(starts, starts[1:]):
            sid = hashlib.sha256(f'{rel}:{a}'.encode()).hexdigest()[:16]
            heading = lines[a].strip().lstrip('# ').strip() if lines[a].startswith('#') else '入口契约'
            sections[sid] = {'path': rel, 'heading': heading, 'line_start': a+1,
                             'line_end': b, 'content': ''.join(lines[a:b]), 'commit': COMMIT}
            ids.append(sid)
        coverage.append({'path': rel, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'sections': ids})
    save('method-registry/source-sections.yaml', {'sections': sections, 'documents': coverage})
    return sections

def refs(sections, module, heading):
    path = MODULES[module][1]
    matches = [sid for sid, s in sections.items() if s['path'] == path and heading in s['heading']]
    if not matches:
        raise ValueError(f'Source heading missing: {module}/{heading}')
    return matches

# Curated migration map: id | student name | source heading | type | role | trigger | first action.
# Boundary and full teaching facts are retained VERBATIM in section_ids; no broad title is invented as a rule.
CATALOG = {
'reading': [
('R03','换词不换义','同源替换','method','interpreter','选项换了表达，需要核同一断言','并排圈出原文与选项的对象、动作和限定词，逐格核语义是否相同'),
('R04','比较别偷换','比较级谨慎选','method','decider','候选带比较级或最高级','列出比较双方、属性、方向、程度、范围、时间与条件，逐格回文核对'),
('R05','因果别选反','因果选果','method','decider','两个有依据的候选可能属于同一因果链','先圈题干问原因还是结果，再写出原文支持的原因→结果，比较候选落点'),
('R07','并列打包','并列删除','method','reducer','多个细节真实并列且题干允许归为一组','把同层并列项框成一组，核候选是否只截取组内局部'),
('R08','例子只作证','例子非答案','method','interpreter','题干问例子的作用而不是例子细节','圈例子前后被支持的观点，再用例子内容检验它实际支持哪句'),
('R10','代词回填','代词指代','method','interpreter','代词使对象或动作归属不清','列候选先行词，把每个换回原句，核数、动作角色和完整语义'),
('R11','长句拆骨','逻辑简化','method','interpreter','定位长句主干与枝叶混在一起','圈谓语和对应主体，划开修饰枝叶，但保留否定、条件、范围和比较'),
('R12','关键词追踪','跳读定位','method','locator','找不到与题干对象对应的证据句','圈题干有区分力的对象或标签，回文找对应句，再读完整断言'),
('R13','名词追踪','名词定出处','sub_action','locator','题干有可区别于其他段的名词','圈差异性名词，回原文对应区域，不以同词命中直接定案'),
('R14','顺序锁区','名词定出处','sub_action','locator','文章组织与题目顺序实际相符','标相邻已定位题的出处，作为当前题查找区间，发现倒叙或偏离就取消区间'),
('R15','动词定关系','名词定出处','sub_action','interpreter','同一名词对应多个动作关系','圈题干动词，配回主体和对象，与定位句的完整谓语比较'),
('R16','主题锁定','mainly题','framework','framework','题干问全文或指定段主旨','先圈全文/段落范围，再写对象与核心判断，回各关键段检查覆盖'),
('R17','前后补证','定位后上下文核对','method','verifier','定位句缺原因、指代或转折关系','明确缺哪种关系，只向前后扩读到能补清它的句子，再核主体和动作'),
],
'seven-five': [
('F02','句型分组','结构一致','sub_action','reducer','选项存在不同句式且空位有结构线索','一次圈出完整句/半句/疑问/祈使等真实结构并分组，再回正文核内容'),
('F03','主角分组','主语一致','sub_action','reducer','选项谈论的主体或代词不同','圈选项主语与指代对象，按实际主体分组，正文发生话题转换时重新核对'),
('F04','时间分组','时态一致','sub_action','reducer','选项存在真实时间差异','标每项谓语及时间词，按真实事件时间分组，不用分词词尾代替时态'),
('F05','段首统领','总起句做题法','method','interpreter','空位在段首且可能统领下文','列下文共同对象、动作与段落任务，再核候选能否统领，不把段首自动当中心'),
('F06','前后呼应','对应词法','method','verifier','候选与上下句有对象或词义复现','圈两边对应对象与动作，标同指或同义关系，再回填核上下句和段落任务'),
('F07','关系拼接','逻辑关系法','method','verifier','空前后显示转折、因果、解释等关系','写出两侧完整内容，指出实际关系，再核候选连接后是否成立'),
('F08','情绪同向','褒贬一致','sub_action','reducer','同一对象有可确认的评价方向','圈评价词及它评价的对象，比较候选评价维度，不因同为积极词就定案'),
('F09','半句补全','结构一致','sub_action','interpreter','空位与选项是需要拼接的半句','把候选接到现有半句，标主语谓语与连接位置，再检验完整语义'),
('F10','末轮反查','定案与输出','verification_rule','verifier','整篇初填后需要回查','逐空回填，核主体、动作、对象、上下句关系及段落任务，不以占用或剩余定案'),
('F11','正文闭环','定案与输出','internal_rule','decider','候选已回填且必须区分竞争项','逐项核候选主体、动作、对象、上下句关系和段落任务，只以当前空自身的决定性关系定案'),
],
'cloze': [
('C01','语篇线索链','完形语篇逻辑破译','framework','framework','当前空不能由孤立语法闭合','标当前空是词义/关系/搭配角色；找最近对象与动作线索；不足向复现、回答、结果或评价扩；回填核语义'),
('C02','前后夹击','瞻前顾后法','method','verifier','空前空后证据尚未闭合','圈两侧谁、动作、评价和时间；近处不足再向明确复现或结果扩读，仍不足暂留'),
('C03','首句定调','完形语篇逻辑破译','sub_action','interpreter','当前空依赖人物背景或全文基调','从首句记录人物、背景、主题、视角和暂定基调，不据此预编后续情节'),
('C04','词性导航','词性只引导','sub_action','locator','空内词的句法作用能指向线索类型','标空内作用，再圈修饰同一对象或动作的结构，不凭词性定案'),
('C05','近义落地','近义项要落到','sub_action','interpreter','多个候选译义相近或评价同向','并列写出各项具体状态、程度或功能，回原文对象核差异，词义未知就停'),
('C06','时间线复原','逻辑与时间','sub_action','interpreter','空位依赖事件先后或时间间隔','写两件事发生时间及间隔，再标先后或因果，不省略题面时间条件'),
('C07','名词回声','名词复现','sub_action','locator','名词空需要同一人物物件或事件线索','圈原词/同义/同源复现并核是否同一对象，不把复现直接当答案'),
('C08','结果反推','评价、结果与动作链','sub_action','verifier','题面给出评价或结果可核当前行为','先还原结果所评价的具体行为，再核候选是否有真实题面联系，不能由猜定空互证'),
('C09','动作串联','评价、结果与动作链','sub_action','interpreter','连续动作需要先后或因果衔接','按已有动作画先后链，逐个标连接关系，不增添题面没有的时长或因果'),
],
'grammar': [
('G02','双路分流','总路线','sub_action','framework','开始处理语法空位','只标有/无提示词，再回完整句确认位置功能，不先改提示词'),
('G03','限定词落位','冠词','internal_rule','decider','名词前缺限定且确认为冠词路线','圈中心名词、单复数和已有修饰，回语境核特指泛指再定冠词'),
('G04','指代落位','代词','internal_rule','decider','空位需要代词或所有格功能','标空位作主语/宾语/限定/反身功能，回指实际对象再用节点规则'),
('G05','介词看场景','介词','method','decider','空位已判需要介词','圈介词后的中心词及所属动作，核场景关系或固定搭配，陌生搭配不猜'),
('G06','从句找缺口','连词、关系词','method','decider','句间连接位置且可能是从句','分别圈两侧谓语，核从句是否缺主语、宾语、表语或状语，再判连接功能'),
('G07','句间搭桥','句间逻辑','method','decider','两个结构完整的句子缺逻辑连接','写两侧完整意思，标实际转折/因果/并列等关系，不由单个提示词定案'),
('G08','词性落位','有提示词','method','reducer','有提示词但不确定空位需要什么','圈空位前后修饰与支配结构，标名/形/副/代/数/动功能，再进对应分支'),
('G09','名词节点','名词及所有格','internal_rule','decider','空位已确认需名词或所有格','圈限定、数量和所有关系，核派生、单复数或所有格，不见提示动词就进动词路线'),
('G10','形副节点','形容词、副词','internal_rule','decider','空位确定作修饰或表语','圈被修饰词和比较结构，判形/副及级别，不机械加比较级'),
('G11','数词节点','数词','internal_rule','decider','空位已确定需要数量或顺序','圈数量/次序线索，按节点规则处理基数、序数或词形'),
('G12','动词二分','第一步：数谓语','method','reducer','空位已确认需要动词形式','圈句内已有谓语与连接词，核空位是否承担谓语，再分谓语/非谓语'),
('G13','时态三查','谓语：检查','sub_action','decider','空位是谓语且需判时态','圈明确时间、上下文事件先后和句内语态，再与真主语核数'),
('G14','找真主语','谓语：检查','sub_action','verifier','主谓间有修饰造成数判断混乱','划开插入和修饰，圈真正主语中心词，核谓语一致，保留否定条件'),
('G15','非谓语三轴','非谓语：作用','method','decider','空位已确认非谓语','标句法作用、逻辑主语与动作的主被动、同谓语的先后关系，再选择形式'),
('G16','找动作主人','26S春 补充','sub_action','verifier','非谓语动作归属尚不明确','圈非谓语的逻辑主语，再核谁执行或承受动作，不只看最近名词'),
('G17','长句脱壳','总路线','sub_action','interpreter','长句修饰妨碍识别空位成分','圈主干谓语和对应主语，暂划介词短语、非谓语、插入语和从句，再恢复决定空位的修饰、否定与条件'),
('G18','考点重复反查','总路线','verification_rule','verifier','整篇完成后核对考点分布','列每空实际考点，发现重复只触发回查，不能推翻该空独立句法语义证据'),
('G19','变形次数反查','总路线','verification_rule','verifier','提示词初变形后需要复核','对照原提示词与空位成分记录变形路线，一般一次只是回查提示，不凭次数选答案'),
],
'application-writing': [
('A01','作文五检','批改顺序：先五审法','framework','framework','应用文题面要点或稿件任务不清','按文体、对象、要点、逻辑、语言逐栏记录题面与原稿证据，先任务后语言'),
('A02','六步成稿','六步训练法','framework','framework','有题目但需要从审题到成稿路线','先圈限定和全部要点，搭文体骨架，再依原六步造句、组篇、升级和复核'),
('A03','三步造句','三种句子生成法','method','interpreter','要点已确定但简单句写不出来','先写主体，再写动作或状态，最后嵌入题面支持的场景细节'),
('A04','句块拼接','三种句子生成法','method','interpreter','多个动作要合成复杂句','每个动作先写正确简单句，再按真实关系用从句、非谓语或连接词粘连'),
('A05','长句重组','三种句子生成法','method','interpreter','中文长句信息和修饰混杂','拆核心与修饰，按主体→动作→场景重组，再校时态词性单复数与风格'),
('A06','对照仿写','富兰克林写作法（五步）','framework','framework','课后需积累准确可迁移表达','先简化中文自行译，再对照范文记录缺失表达；背诵复现后在同结构仿写'),
('A07','长句搭积木','反向劫匪插葱','method','interpreter','基础句准确且需要自然升级','先简化中文、译正确简单句，再加入服务真实逻辑的修饰或从句，搭配不明停升级'),
('A08','文体骨架','常见文体骨架','category','framework','应用文需要匹配文体与交际目的','圈题目文体对象目的，调用对应骨架，不把文体模板算独立原创规则'),
('A09','应用文评分','15 分评分规范','internal_rule','verifier','题目与学生全文可见且请求批改','先按15分五档三维定档，逐条引用题面和原稿证据，缺材料不完整给分'),
('A10','读背仿与训练阶段','复习路径与分数锚定','framework','framework','课后需要规划作文训练而非现场答案','按材料中的训练阶段选一个下一步，不把分数锚定当个体提分保证'),
],
'continuation-writing': [
('W01','五步锁剧情','开明致学五步法','framework','framework','原文与两段开头语齐全，需要构思','先读两段开头语找约束，再记录原文人物矛盾与时空，依跳定思提润推进'),
('W02','十句五锚','十句五定法','framework','framework','需要搭两段功能提纲或诊断桥接','只标学生自写的第1/5/6/9/10句功能，写清衔接、桥接、解决与回扣，不算给定首句'),
('W03','剧情四格','情节构思：PTSD','framework','framework','已读原文首句需要整理情节','只选需求→困难→行动→结局这一套四格，每格填原文约束，不混用另一版字母定义'),
('W04','首句找缺口','gap 读法','method','locator','两段开头语对人物或行动有约束','圈开头语的名词和任务，回文找人物与矛盾，再反推段间需要补的动作'),
('W05','动作拆链','动作链与动作面','method','interpreter','核心行动需要具体连贯描写','把已有行动拆最多三个合理小动作，再加与场景相符的方式，不改变人物能力'),
('W06','三点锁题','五档升级路径','sub_action','locator','续写不知从哪里下笔','圈核心人物、核心矛盾和关键线索，不额外造主角或无铺垫事故'),
('W07','伏笔回扣','五档升级路径','sub_action','verifier','人物行为或物件需要兑现原文线索','把关键行为与原文伏笔逐对连线，找悬空线索，不强行用无关细节'),
('W08','因果三连','五档升级路径','sub_action','interpreter','事件跳跃缺因果桥梁','写因为A→行动B→结果C，每条边引用原文或合理铺垫，不让猜测互证'),
('W09','细节三镜','五档升级路径','sub_action','interpreter','主线成立但画面单薄','在推进主线的位置选动作、神态、环境中有用的细节，不每句堆三类'),
('W10','无痕衔接','五档升级路径','sub_action','interpreter','连接词堆砌却对象衔接不清','圈相邻句共同对象和代词回指，使用关键词复现，不删掉必要逻辑关系'),
('W11','小转折','五档升级路径','sub_action','interpreter','解决过程可以加入有铺垫波折','从原文矛盾找小障碍，写解决动作，不凭空新增关键人物事故'),
('W12','精准换词','五档升级路径','sub_action','interpreter','基础表达准确后需改具体词','圈笼统动词或形容词，用符合场景与搭配的具体词替换，生词搭配不明就停'),
('W13','结尾回扣','素材与考点','method','verifier','故事结局需要回应主题','圈原文关键细节与解决结果，让结尾回扣它们；独立升华句不是必须项'),
('W14','骨架句与肌肉句','肌肉句与骨架句','category','framework','功能提纲与扩写位置需要区分','标确定功能位为骨架，其余位置按因果与画面扩写，不把句数当评分扣分项'),
('W15','续写评分','25 分评分规范','internal_rule','verifier','原文首句和学生续写齐全且请求评分','只按25分续写档次核原文融洽、语言与结构；不抄首句正常，书写只在实见影响交际时评'),
('W16','五档训练升级','五档升级路径','framework','framework','课后需确定下一档训练缺口','按现稿证据选对应升级动作，不把训练模板直接当官方独立扣分项'),
],
}

def migrate(golden_only=False):
    sections = import_sections()
    index = yaml.safe_load((ROOT/'method-registry/registry.yaml').read_text(encoding='utf-8'))
    old = {}
    for f in index['method_files']:
        for m in yaml.safe_load((ROOT/f).read_text(encoding='utf-8'))['methods']:
            old[m['method_id']] = m
    focus = ['R01','R02','R06','R09','F01','G01']
    for mid in focus:
        m = old[mid]
        if m['version'] == '1.0.0':
            save(f'method-registry/history/{mid}/1.0.0.yaml', m)
        module = next(k for k,v in MODULES.items() if v[0] == m['question_type'])
        source_heading = {'R01':'过度推测','R02':'主客一致','R06':'主旨缺失','R09':'三化法','F01':'结构一致','G01':'总路线'}[mid]
        m['section_ids'] = refs(sections, module, source_heading)
        if mid == 'F01':
            m['section_ids'] += refs(sections,module,'主语一致') + refs(sections,module,'时态一致')
        if mid == 'G01':
            m['section_ids'] = [sid for sid,s in sections.items() if s['path']==MODULES['grammar'][1]]
        guide = next((ROOT/'student-guides').glob(mid+'-*.md')).read_text(encoding='utf-8')
        for key, duration in [('10s','10'),('30s','30'),('90s','90')]:
            pattern = rf'## {duration} 秒版\s+([\s\S]*?)(?=\n## |\Z)'
            m['compact'][key] = re.search(pattern, guide).group(1).strip()
        m.update(method_type='framework' if m['primary_role']=='framework' else 'method',
                 maturity_status='candidate', practical_value='Useful', version='1.1.0',
                 change_reason='统一 compact、源章节、角色与版本；保留既有判据和刹车边界',
                 affected_cases=list(m['cases'].values()), regression_result='pending_automated_run')
        m['first_use_test']['failure_type'] = None
        if isinstance(m['verification'], list):
            m['verification'] = '\n'.join(m['verification'])
        m['student_ready'] = True
        if mid == 'G01':
            m['core_action'] = '圈出空后的括号提示词（若有），再圈空前后支配或修饰词，在未填句上标明空位成分；确认需要动词才分谓语/非谓语。'
        m['role_correctness'] = {'declared_primary_role':m['primary_role'],'observed_actual_role':None,'role_match':None,'overclaim_detected':None,'notes':'pending_real_participant_validation'}
        m['short_version_safety'] = [{'version':v,'false_trigger_rate':None,'boundary_accuracy':None,'role_overclaim_rate':None,'stop_rule_failure_rate':None,'safe_for_release':'untested'} for v in ['10s','30s','90s']]
        m['evaluation']['boundary_accuracy'] = None
        m['entry_copy'] = guide.split('## 四步实战卡')[0].split('\n',1)[1].strip()
        hard = f'cases/{mid}/hard/case.yaml'
        if not (ROOT/hard).exists():
            save(hard, {'method_id':mid,'case_type':'hard','status':'evidence_gap','objective':'复杂多线索边界回归','prompt_excerpt':None,'expected_action':m['core_action'],'pass_condition':'无真实题面不得假设通过','source_reference':m['source_references'][0],'gap':'缺少经核验完整困难题，不造题补数'})
        m['cases']['hard'] = hard
    grouped = {k:[m for mid,m in old.items() if mid in focus and m['question_type']==v[0]] for k,v in MODULES.items()}
    if not golden_only:
        for module, rows in CATALOG.items():
            for mid, name, heading, kind, role, trigger, action in rows:
                sids = refs(sections,module,heading)
                source = sections[sids[0]]
                boundary = '不能以本动作代替完整题面关系核验；题面缺失、关键词义不明或出现反证就停止定案。具体边界见源章节。'
                if role in {'locator','reducer','interpreter','framework'}:
                    boundary = '本步骤只产生'+{'locator':'位置','reducer':'缩小范围','interpreter':'语义结构','framework':'框架'}[role]+'，不能自动定案。'+boundary
                output = {'locator':'locate','reducer':'reduce','interpreter':'interpret','framework':'interpret','decider':'decide','verifier':'verify'}[role]
                ref = {'repository':index['source_baseline']['repository'],'commit':COMMIT,'path':source['path'],'heading':source['heading']}
                casepath = f'cases/{module}/{mid}/canonical/case.yaml'
                save(casepath, {'case_id':mid+'-canonical','method_id':mid,'question_type':MODULES[module][0],'source':ref,'question':None,'answer':None,'trigger':trigger,'evidence':[],'method_role':role,'expected_action':action,'expected_output':output,'stop_rule':boundary,'case_type':'canonical','status':'evidence_gap','notes':'源方法可核；尚未逐题核验案例，不可当成功样例'})
                m = dict(method_id=mid,brand_name=name,source_name=source['heading'],aliases=[source['heading']],question_type=MODULES[module][0],method_type=kind,role=role,primary_role=role,secondary_roles=[],output_type=output,student_symptoms=[trigger],trigger_cues=[trigger],core_action=action,decision_rule='执行动作后逐条对照源章节判据；不足则暂留，不能据关键词或剩余项定案。',verification='回填或回原文逐条核主体、动作、限定和当前任务，见源章节完整规则。',stop_rule=boundary,common_wrong_instinct='只记方法名或表面线索，跳过当前题面关系核验。',failure_cases=['缺完整题面或关键语义不能确认时强行定案'],counterexamples=['表面触发信号存在，但完整关系不支持时不能继续；真实反例题面待核'],transfer_pattern='在新题面重复同一具体动作，不迁移上一题答案。',memory_line=action,anti_rule='动作产物 ≠ 自动答案。',visual_formula=f'{trigger}\n↓\n{action}\n↓\n{output}（未必定案）',challenge_prompt='先不报答案，只在题面标出：'+action,source_references=[ref],section_ids=sids,can_follow=[],usually_before=[],usually_after=[],conflicts_with=[],cannot_replace=['完整题面验证'],levels={'compact':'动作入口','full':'源章节判据'},compact={'10s':trigger+'。'+action+'。'+boundary,'30s':trigger+'。'+action+'。判断与停止：'+boundary,'90s':trigger+'。'+action+'。完整规则必须读取对应源章节；案例未核，不编示范答案。'+boundary},full={'section_ids':sids,'source_boundary':boundary},cases={'canonical':casepath},four_step_card={'start':trigger,'first_cut':action,'judge':'逐条核源章节判据，不足则继续找独立证据。','stop':boundary},practicality_gate={'status':'design_complete_empirical_pending','trigger':trigger,'action':action,'output':output+'；严格限制主职责','stop':boundary,'transfer':'迁移同一动作，不迁移原题答案','efficiency':'未测；预期价值是显式化动作和边界，不保证提速','misuse_cost':'未测；误触发时不得定案'},first_use_test={'status':'designed_not_run','trigger_success':None,'action_success':None,'evidence_success':None,'stop_rule_success':None,'no_answer_backfit':None,'failure_type':None,'final_result':'pending_real_student_test'},evaluation={'baseline':'普通逐项核题面','primary_benefit_hypothesis':'显式化下一步动作和证据边界',**{k:None for k in ['trigger_precision','trigger_recall','resolution_rate','standalone_rate','assist_rate','false_trigger_rate','transfer_rate','boundary_accuracy','time_complexity_gain']}},usefulness_level='Useful',status='candidate',maturity_status='candidate',practical_value='Useful',version='1.0.0',change_reason='首次迁移现有激活章节；非黄金短版尚未逐一教学审查',affected_cases=[casepath],regression_result='pending_automated_run',student_ready=False)
                grouped[module].append(m)
                if mid == 'C01':
                    m['secondary_roles'] = ['decider']
                    m['secondary_role_gate'] = '框架产物不足以定案；只有逐项比较具体词义、当前空自身决定性关系并回填闭合后，才以显式 decider 阶段提交。'
                if mid == 'G13':
                    m['source_name'] = '时态判定三步法'
                    m['aliases'].append('时态判定三步法')
                if mid == 'W03':
                    m['source_alias'] = 'PTSD'
    index['method_files'] = []
    index['methods'] = {}
    for module, methods in grouped.items():
        if not methods:
            continue
        path = f'method-registry/{module}.yaml'
        save(path, {'methods':methods})
        index['method_files'].append(path)
        for m in methods:
            index['methods'][m['method_id']] = {k:m[k] for k in ['brand_name','status','version']}
            index['methods'][m['method_id']]['file'] = path
    index['registry_version'] = '2.0.0'
    index['golden_methods'] = focus
    index['schema'] = 'schemas/method-card.json'
    index['source_sections'] = 'method-registry/source-sections.yaml'
    save('method-registry/registry.yaml', index)
    for mid in focus:
        m = old[mid]
        m['student_ready'] = True
    # Update legacy contract for compatibility tests; executable JSON Schema is separate.
    schema = yaml.safe_load((ROOT/'method-registry/schema.yaml').read_text(encoding='utf-8'))
    schema['case_types'] = ['canonical','counterexample','boundary','transfer','hard']
    save('method-registry/schema.yaml', schema)
    manifest = [{'path':p.relative_to(SOURCE).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(SOURCE.rglob('*')) if p.is_file()]
    save('provenance/manifest.yaml', {'repository':index['source_baseline']['repository'],'commit':COMMIT,'files':manifest,'usage':'只读审计快照，不是运行时人工维护事实源'})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--golden-only', action='store_true')
    parser.add_argument('--rebuild', action='store_true',help='Explicitly rebuild the imported registry, replacing its current edited cards')
    args = parser.parse_args()
    existing=yaml.safe_load((ROOT/'method-registry/registry.yaml').read_text(encoding='utf-8'))
    if existing['registry_version']=='2.0.0' and not args.rebuild:
        raise SystemExit('Initial migration already complete; edit Registry and regenerate projections instead. --rebuild replaces current cards.')
    migrate(args.golden_only)
