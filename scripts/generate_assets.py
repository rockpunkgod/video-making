"""Generate public projections from Registry; --check rejects manual drift."""
import argparse
import yaml
from core.registry import ROOT, Registry, load

def build():
    r = Registry()
    assets = {}
    for mid,m in r.methods.items():
        if not m.get('student_ready'): continue
        parts = [f'# {mid} {m["brand_name"]}：学生首次接触版', m['entry_copy'], '## 四步实战卡']
        parts += [f'{i}. {label}：{m["four_step_card"][key]}' for i,(key,label) in enumerate([('start','启动'),('first_cut','第一刀'),('judge','判断'),('stop','停止')],1)]
        parts += ['Stop Rule：'+m['stop_rule']]
        for duration in ['10','30','90']:
            parts += [f'## {duration} 秒版',m['compact'][duration+'s']]
        parts += ['## 一屏视觉式','```text\n'+m['visual_formula']+'\n```','反口诀：'+m['anti_rule'],'## 为什么容易错',m['common_wrong_instinct'],'## 反例与挑战','反例/边界示意（不等于已核验真题）：'+'；'.join(m['counterexamples']),m['challenge_prompt'],f'生成来源：Registry {mid}@{m["version"]}。student_ready仅表示静态学生入口齐备，真人验收待运行。']
        assets[f'student-guides/{mid}-{m["brand_name"]}.md'] = '\n\n'.join(parts)+'\n'
    symptoms = {'routes':[]}
    for m in r.methods.values():
        aliases=next((x['phrases'] for x in r.symptom_cues if x['method_id']==m['method_id']),[])
        symptoms['routes'].append({'question_type':m['question_type'],'symptoms':m['student_symptoms'],'spoken_aliases':aliases,'method_id':m['method_id'],'role':m['primary_role'],'first_action':m['core_action'],'stop_rule':m['stop_rule']})
    assets['references/student-symptoms.yaml'] = yaml.safe_dump(symptoms,allow_unicode=True,sort_keys=False)
    assets['references/student-symptoms.md'] = '# 学生卡点导航（自动生成）\n\n'+'\n\n'.join(f'{x["question_type"]}：{x["symptoms"][0]} → {x["method_id"]}；第一刀：{x["first_action"]}；停止：{x["stop_rule"]}' for x in symptoms['routes'])+'\n'
    tree=r.grammar_tree
    tree_copy='# 语法知识节点导航（自动生成）\n\n有无提示词只决定入口；空位功能必须从未填句取证。树不直接报答案。\n\n'
    tree_copy+='```text\n'+r.methods['G01']['visual_formula']+'\n```\n\n'
    def node_name(nid):
        names=[r.methods[mid]['brand_name'] for mid in tree['nodes'][nid]['methods']]
        return ' / '.join(names) if names else {'without_hint':'无提示词：判功能','hint':'有无提示词','with_hint':'有提示词：判空位成分'}.get(nid,'待题面确认功能')
    tree_copy+='\n\n'.join(f'{node_name(nid)} → {"、".join(node_name(child) for child in n["children"]) or "按本节点规则核验"}；方法：{", ".join(n["methods"]) or "待题面确认功能"}' for nid,n in tree['nodes'].items())
    tree_copy+='\n\n先拆句：'+', '.join(tree['preparatory_methods'])+'；整篇复查：'+', '.join(tree['postcheck_methods'])+'。都不能代替独立答案证据。\n'
    assets['references/grammar-navigation.md']=tree_copy
    assets['gaokao-grammar-fill/references/grammar-navigation.md']=tree_copy
    anti = load('method-registry/anti-rules.yaml')['rules']
    assets['references/anti-rules.yaml'] = yaml.safe_dump({'rules':anti},allow_unicode=True,sort_keys=False)
    assets['references/anti-rules.md'] = '# Anti-Rule Registry（自动生成）\n\n'+'\n\n'.join(f'## {x["anti_rule_id"]} {x["rule"]}\n\n绑定：{", ".join(x["related_methods"])}。反例与边界：{x["boundary"]}。依据：{", ".join(x["source_evidence"])}。仅源模式，不是真题验证。' for x in anti)+'\n'
    for name,types in [('gaokao-english',['阅读理解','七选五','完形填空']),('gaokao-objective',['阅读理解','七选五','完形填空']),('gaokao-grammar-fill',['语法填空']),('gaokao-writing',['应用文','读后续写'])]:
        source_name = 'gaokao-english' if name=='gaokao-objective' else name
        original = r.document(source_name+'/SKILL.md')
        front_end = original.split('---',2)[2].lstrip()
        description = '高考英语'+ '、'.join(types)+'答疑；经注册表、证据核验与独立输出适配。'
        assets[f'{name}/SKILL.md'] = f'---\nname: {name}\ndescription: {description}\n---\n\n# 统一引擎适配入口\n\n先读取本目录 [generated-contract.md](generated-contract.md)，再按题型读取其中链接的 references，保留原先题型、顺序与证据边界。课程原名和品牌名是同一方法的别名，不产生新判据。学生动作入口允许注册品牌名，方法问答同时兼容课程原名。源契约中的逆推只能用于独立核验，不得把已知答案当证据或在 First-use 先猜后贴方法。\n\n方法查询：在项目根执行 `python -m answer_engine method METHOD_ID`；单题：`python -m answer_engine analyze INPUT.json --renderer legacy-wechat`；整卷：`python -m answer_engine paper INPUT.json`。宿主模型按完整契约作语义分析，再提交有原文跨度、判据、刹车、回填和审阅者的 relations；核心不把宿主猜测当自动验证。缺题面或语义证据必须暂留，不填答案。写作完整批改仍由宿主按15/25分独立契约完成，不由本地程序伪评分。\n\n单独安装 Skill 文件夹时，生成资源可自包含调用，完整核心命令需整个仓库及依赖；不要假定安装 Skill 等于安装核心。不能执行程序时按题型查询 [generated-methods.yaml](generated-methods.yaml)，完成相同证据动作；明确标记宿主分析未经核心检查。不要绕开停用边界。\n'
        if name=='gaokao-grammar-fill':
            assets[f'{name}/SKILL.md']+='\n语法知识路由读取 [grammar-navigation.md](references/grammar-navigation.md)。先确认有无提示词，再按未填句功能进入节点；树路径只是知识调用计划，不能代替句法、搭配与词形核验。\n'
        if name in {'gaokao-english','gaokao-objective','gaokao-grammar-fill'}:
            assets[f'{name}/SKILL.md']+='\n需要完整单题口播进入核心时读 [lesson-review.md](references/lesson-review.md)，提交lesson_review并绑定实际动作、短引文、候选比较和刹车。完整口播没有闭合就扣留，不把通用结构投影当原课程现场讲解；整篇顺序仍须原契约完整执行，不由单题通道证明。\n'
            assets[f'{name}/references/lesson-review.md']='<!-- Generated interface guide; course facts stay in Registry. -->\n\n'+(ROOT/'docs/lesson-review.md').read_text(encoding='utf-8')
            assets[f'{name}/SKILL.md']+='\n整篇讲题进入核心时读 [passage-lesson.md](references/passage-lesson.md)，用lesson命令提交原题号、共享原文及有证据的实际顺序/暂留/回收；不能直接拼单题消息冒充整篇，不凭篇号或答案键猜顺序。\n'
            assets[f'{name}/references/passage-lesson.md']='<!-- Generated interface guide; course facts stay in Registry. -->\n\n'+(ROOT/'docs/passage-lesson.md').read_text(encoding='utf-8')
        if name=='gaokao-writing':
            assets[f'{name}/SKILL.md']+='\n完整写作审阅进入核心时读取 [writing-review.md](references/writing-review.md)，提交writing_review而非用客观题relations假装评分。区分确定错误与可选润色，独立15/25分规范、材料与书写边界不变；程序只检查引用/交付结构，分数仅外部建议。\n'
            assets[f'{name}/references/writing-review.md']='<!-- Generated interface guide; course facts stay in Registry. -->\n\n'+(ROOT/'docs/writing-review.md').read_text(encoding='utf-8')
        assets[f'{name}/generated-contract.md'] = '<!-- Generated from Registry; DO NOT EDIT. -->\n\n'+front_end
        assets[f'{name}/generated-methods.yaml'] = yaml.safe_dump({'methods':[m for m in r.methods.values() if m['question_type'] in types]},allow_unicode=True,sort_keys=False)
        for doc in r.sources['documents']:
            path = doc['path']
            if path.startswith(source_name+'/references/'):
                assets[name+'/'+path.split('/',1)[1]] = r.document(path)
    for d in r.sources['documents']:
        if d['path'].startswith('agents/'):
            assets[d['path']] = '<!-- Generated compatibility contract; installed Skill uses Registry. -->\n'+r.document(d['path'])
    assets['references/method-roles.md'] = '# 方法角色（自动生成）\n\n'+'\n'.join(f'- {m["method_id"]} {m["brand_name"]}：{m["method_type"]} / {m["primary_role"]} → {m["output_type"]}' for m in r.methods.values())+'\n'
    return assets

def generate(check=False):
    stale = []
    for relative, content in build().items():
        p = ROOT/relative
        if check:
            if not p.exists() or p.read_text(encoding='utf-8') != content:
                stale.append(relative)
        else:
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(content,encoding='utf-8')
    if stale:
        raise ValueError('Stale generated assets: '+', '.join(stale))
    return {'generated_assets':'PASS'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    print(generate(parser.parse_args().check))
