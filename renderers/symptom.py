"""Student-facing obstacle navigation, not verified triggers or question solving."""
from core.matcher import symptom_route
from core.registry import Registry


def render_symptom(question_type,symptom,registry=None):
    registry=registry or Registry()
    registry.validate()
    types={method['question_type'] for method in registry.methods.values()}
    if question_type not in types:
        raise ValueError('Unsupported question type for symptom guidance')
    routes=symptom_route(question_type,symptom,registry,include_defaults=False)
    ids={route['method_id'] for route in routes}
    # A coverage diagnosis does not construct its own paragraph/full-text core.
    if ids and ids <= {'R06','R09','R16'}:
        selected=next((mid for mid in ('R16','R09') if mid in ids),None)
    else:
        selected=routes[0]['method_id'] if len(routes)==1 else None
    if selected is None:
        prompts={
            '阅读理解':'是找不到对应原文，原句读不懂，还是两个选项难比较。主旨题还需说清问全文还是指定段落。',
            '七选五':'是七个选项都像能填，段首空没有思路，还是重复词让你拿不准。',
            '完形填空':'是这个空的词义不明，找不到前后提示，还是几个候选都能读通。',
            '语法填空':'是有无提示词没确认，空位成分看不出，还是分不清谓语和非谓语。',
            '应用文':'是题面要点没写全，基础句写不出，还是已有句子的语法或表达卡住。',
            '读后续写':'是两段剧情没接通，首句的缺口没找出，还是一个行动不知道怎么写。',
        }
        return '先把卡点说具体一点，'+prompts[question_type]+'请补这一处的题面或原句，先不猜答案，也不从方法名里硬挑一个。'
    method=registry.methods[selected]; card=method['four_step_card']
    outputs={'locate':'证据位置','interpret':'句意、框架或知识节点','reduce':'优先核查的候选范围',
             'decide':'当前候选的一项判断','verify':'核验结果'}
    first_cut=card['first_cut']; judge=card['judge']; start=card['start']
    output_label=outputs[method['output_type']]
    if selected=='G01': output_label='下一知识节点'
    # In an explicitly sentence-reading obstacle, expose the source-bound
    # sentence action first. Other established interpretation branches remain
    # in the full card rather than becoming mandatory first-use steps.
    if selected=='R11' and any(cue in symptom for cue in ('长句','句子','定位句')):
        first_cut=first_cut.split('；',1)[0]
        judge=judge.split('；',1)[0]
        start=start.split('，或',1)[0]
        output_label='核心句意或关系'
    support=method.get('full',{}).get('beginner_support')
    action_lines=['第一刀，'+first_cut]
    if support:
        action_lines=['第一刀，'+support['first_micro_action'],
                      '继续核完整动作，'+first_cut]
    return '\n\n'.join([
        '先考虑'+method['brand_name']+'这个入口。这里只根据卡点提出建议，是否适用还要核题面。',
        '什么时候启动，'+start,
        *action_lines,
        '这一入口负责产出'+output_label+'，'+judge,
        '什么时候停，'+card['stop'],
        *(['如果卡住，'+support['if_stuck']] if support else []),
        '请把对应题干和原句贴出来，再核这一步是否真的触发。现在不报答案。',
    ])
