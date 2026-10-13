"""Navigate registered grammar dependencies without inventing syntactic truth."""
from .evidence import check_span
import re

def hint_branch(question):
    """Keep missing metadata unknown unless a target-bound review establishes absence.

    A review annotates the printed question; it never inserts/changes given_word.
    The span checks certify the cited characters, not review identity or semantics.
    """
    hint=question.get('given_word','')
    branch='without_hint' if 'given_word' in question and hint is None else 'with_hint' if isinstance(hint,str) and hint.strip() else 'unknown'
    review=question.get('grammar_hint_review')
    if review is None:
        return branch
    if question['question_type']!='语法填空':
        raise ValueError('Grammar hint review requires a grammar question')
    spans=[check_span(question,s) for s in review['evidence']]
    if review['review_status']!='reviewed':
        return branch
    if not review['reviewer'].strip() or not review['review_notes'].strip():
        raise ValueError('Hint absence review requires named reviewer and concrete notes')
    if review['state']!='without_hint' or branch=='with_hint':
        raise ValueError('Hint review contradicts the supplied prompt word')
    marker=review['target_marker']
    if not re.fullmatch(r'_{2,}(?:\d+_{2,})?', marker):
        raise ValueError('Hint review target must be a printed blank marker')
    # Do not borrow another blank's absence or infer from a cropped quotation.
    # Ambiguous whole-passage requests must first identify one target blank.
    pattern=r'_{2,}(?:\d+_{2,})?'
    requested=re.findall(pattern,question['stem'])
    if requested and requested!=[marker]:
        raise ValueError('Hint absence review must bind one exact requested blank')
    contexts=[]
    for field in ['passage','stem']:
        text=question.get(field,'')
        if not text or marker not in text: continue
        if text.count(marker)!=1 or (not requested and re.findall(pattern,text)!=[marker]):
            raise ValueError('Hint absence review must bind one exact requested blank')
        start=text.index(marker); end=start+len(marker); suffix=text[end:]
        following=suffix.lstrip()
        if not following: continue
        if following.startswith(('(', '（', '[', '【', '{', '｛')):
            raise ValueError('Target is followed by a bracketed prompt or unresolved parenthesis')
        contexts.append((field,start,end+len(suffix)-len(following)))
    if not contexts:
        raise ValueError('Hint absence needs text after the target, not a cropped blank')
    if not any(s['field']==field and s['start']<=start and s['end']>following_index
               for field,start,following_index in contexts for s in spans):
        raise ValueError('Hint review quote must cover target and following printed text')
    return 'without_hint'


def navigate_grammar(question,registry):
    if question['question_type']!='语法填空':
        if 'grammar_hint_review' in question: hint_branch(question)
        return None
    tree=registry.grammar_tree; nodes=tree['nodes']
    branch=hint_branch(question)
    reviewed=set()
    for obs in question.get('observations',[]):
        for span in obs['evidence']: check_span(question,span)
        if obs['reviewed']: reviewed.add(obs['method_id'])
    # Only external, separately reviewed trigger annotations identify specific
    # functions. Hint spelling or its original POS NEVER identifies a leaf here.
    paths=[]
    if branch!='unknown':
        def walk(nid,path):
            path=path+[nid]
            if nid not in {'entry','hint'} and reviewed.intersection(nodes[nid]['methods']):
                paths.append(path)
            children=nodes[nid]['children']
            if nid=='hint': children=[branch]
            for child in children: walk(child,path)
        walk(tree['root'],[])
    # Keep the deepest path rather than repeating its ancestor confirmations.
    paths=[p for p in paths if not any(len(other)>len(p) and other[:len(p)]==p for other in paths)]
    result={'hint_branch':branch,'status':'needs_hint_confirmation' if branch=='unknown' else 'navigation_planned' if paths else 'needs_function_confirmation','paths':paths,'next_node':paths[0][-1] if len(paths)==1 else 'hint' if branch=='unknown' else branch,'review_basis':'reviewed_trigger_routing_only','limitations':['树路径只展示知识调用依赖，不证明句法、词形或答案；多条路径表示仍需核竞争功能，不能任选一条。','缺少given_word标注时先确认有无提示，不从提示词原词性推断空位功能。']}
    if 'grammar_hint_review' in question:
        result['limitations'].append(
            '无提示状态来自针对本空的外部审阅，未增改原given_word；引文一致不认证审阅身份或英语语义。'
            if question['grammar_hint_review']['review_status']=='reviewed' else
            '无提示注释尚未审阅，不能用它补齐原字段的未知状态。')
    return result
