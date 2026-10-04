"""Navigate registered grammar dependencies without inventing syntactic truth."""
from .evidence import check_span

def navigate_grammar(question,registry):
    if question['question_type']!='语法填空': return None
    tree=registry.grammar_tree; nodes=tree['nodes']
    hint=question.get('given_word','')
    branch='without_hint' if 'given_word' in question and hint is None else 'with_hint' if isinstance(hint,str) and hint.strip() else 'unknown'
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
    return {'hint_branch':branch,'status':'needs_hint_confirmation' if branch=='unknown' else 'navigation_planned' if paths else 'needs_function_confirmation','paths':paths,'next_node':paths[0][-1] if len(paths)==1 else 'hint' if branch=='unknown' else branch,'review_basis':'reviewed_trigger_routing_only','limitations':['树路径只展示知识调用依赖，不证明句法、词形或答案；多条路径表示仍需核竞争功能，不能任选一条。','缺少given_word标注时先确认有无提示，不从提示词原词性推断空位功能。']}
