from copy import deepcopy
from .registry import Registry, validate_schema
from .matcher import match_methods
from .composer import compose, bind_contract
from .execution import execute_actions, validate_execution_trace
from .evidence import EvidenceGraph, check_span
from .grammar_navigation import navigate_grammar
from .writing_feedback import writing_feedback, validate_writing_projection
from .lesson_feedback import lesson_feedback, validate_lesson_projection

class QuestionAnalyzer:
    def __init__(self,registry=None,review_provider=None):
        self.registry = registry or Registry()
        self.review_provider = review_provider

    def analyze(self,question):
        q = deepcopy(question)
        validate_schema('question-input',q)
        if self.review_provider is not None:
            # A provider receives course facts, never an answer key. Its returned annotations
            # are still external semantic assertions, NOT automatically proven truths.
            # Keep a separate snapshot: a provider may mutate its argument in place.
            original = deepcopy(q)
            q = self.review_provider(q,self.registry)
            validate_schema('question-input',q)
            material_fields = ('question_id','question_type','stem','passage','options',
                               'given_word','student_text','continuation_starters',
                               'original_images','student_symptoms')
            for field in material_fields:
                if (field in q)!=(field in original) or q.get(field)!=original.get(field):
                    raise ValueError('Review provider cannot replace original question material: '+field)
        matches = match_methods(q,self.registry)
        chain = compose(q,matches,self.registry)
        graph = EvidenceGraph()
        graph.node('question_signal',q['stem'] or '空题干；只允许结构路由')
        triggers = []
        trigger_nodes = {}
        for obs in q.get('observations',[]):
            for span in obs['evidence']:
                span = check_span(q,span)
                triggers.append(span)
                source = graph.node('source_evidence',span['quote'],span=span)
                signal = graph.node('question_signal','方法触发观察',method_id=obs['method_id'],reviewed=obs['reviewed'])
                graph.edge(source,signal,'supports')
                if obs['reviewed']:
                    trigger_nodes.setdefault(obs['method_id'],[]).append(signal)
        candidate_analysis = []
        retained = set()
        eliminated = set()
        allowed = {x['method_id']:x for x in matches}
        limitations = ['方法匹配置信度是规则/审阅等级，不是统计概率。自动跨度检查不证明语义关系正确。']
        matched_ids = {x['method_id'] for x in matches}
        source_risks = [x for x in self.registry.risks if matched_ids.intersection(x['affected_methods'])]
        limitations += ['课程风险 '+x['risk_id']+'：'+x['action'] for x in source_risks]
        complete = True
        relation_nodes = []
        if q['question_type'] in {'阅读理解','七选五','完形填空'}:
            complete = bool(q.get('passage') and q['stem'] and q.get('options'))
        elif q['question_type']=='语法填空':
            complete = bool(q.get('passage') or q['stem'])
        elif q['question_type']=='应用文':
            complete = bool(q['stem'])
        elif q['question_type']=='读后续写':
            complete = bool(q.get('passage') and len(q.get('continuation_starters',[]))==2)
        for rel in q.get('relations',[]):
            mid = rel['method_id']
            if mid not in allowed or not allowed[mid]['trigger_verified']:
                raise ValueError('Relation requires separately reviewed trigger evidence')
            method = self.registry.methods[mid]
            execution_role = rel.get('execution_role',method['primary_role'])
            if execution_role not in [method['primary_role']]+method['secondary_roles']:
                raise ValueError('Undeclared secondary role')
            if execution_role != 'decider' and rel['effect'] != 'undetermined':
                raise ValueError('method_overreach: auxiliary method cannot decide')
            spans = [check_span(q,s) for s in rel['evidence']]
            if not any(s['field'] in {'passage','stem','student_text'} for s in spans):
                raise ValueError('Candidate cannot prove itself')
            if q['question_type'] in {'阅读理解','七选五','完形填空'} and not any(s['field']=='passage' for s in spans):
                raise ValueError('Objective decision needs its own passage evidence')
            if q.get('options') and rel['candidate'] not in q['options']:
                raise ValueError('Unknown candidate')
            reviewed = rel['review_status']=='reviewed' and complete
            if not reviewed:
                limitations.append('未审阅或题面不全的关系不定案。')
            evidence_ids = []
            claim = graph.node('candidate_claim',rel['claim'],candidate=rel['candidate'])
            relation = graph.node('relation',rel['decision_rule_check'],method_id=mid,candidate=rel['candidate'],reviewed=reviewed)
            relation_nodes.append(relation)
            for signal in trigger_nodes.get(mid,[]):
                graph.edge(signal,relation,'supports')
            action = graph.node('method_action',method['core_action'],method_id=mid)
            for span in spans:
                nid = graph.node('source_evidence',span['quote'],span=span)
                graph.edge(nid,relation,'supports')
                evidence_ids.append(nid)
            graph.edge(claim,relation,'supports')
            graph.edge(relation,action,'supports')
            effect = rel['effect'] if reviewed else 'undetermined'
            if effect != 'undetermined':
                decision = graph.node('decision',effect+': '+rel['stop_rule_check'],candidate=rel['candidate'],method_id=mid)
                graph.edge(action,decision,'eliminates' if effect=='eliminate' else 'supports')
                verify = graph.node('verification',rel['verification'],candidate=rel['candidate'],method_id=mid)
                graph.edge(decision,verify,'verifies')
                (retained if effect=='retain' else eliminated).add(rel['candidate'])
                for step in chain:
                    if step['method_id']==mid: step['state']='reviewed'
                if execution_role != method['primary_role'] and not any(x['method_id']==mid and x['role']==execution_role for x in chain):
                    chain.append(bind_contract({'method_id':mid,'role':execution_role,'input':'当前空具体候选差异与独立关系证据；不是框架本身','output':'decide','action':'逐项核具体词义与当前空决定性关系，再回填闭合；'+method['secondary_role_gate'],'stop_rule':method['stop_rule'],'state':'reviewed'}))
            candidate_analysis.append({'candidate':rel['candidate'],'effect':effect,'claim':rel['claim'],'method_id':mid,'reviewer':rel['reviewer'],'evidence_ids':evidence_ids})
        if retained & eliminated: raise ValueError('Contradictory reviewed candidate effects')
        # A supported candidate is not automatically the best/only answer. With
        # supplied alternatives each rival needs its own reviewed elimination.
        unresolved = sorted(set(q.get('options',{})) - retained - eliminated)
        candidate_coverage = not unresolved
        answer = next(iter(retained)) if len(retained)==1 and candidate_coverage else None
        if unresolved:
            limitations.append('仍有未完成决定性核验的候选：'+', '.join(unresolved)+'；保留一个候选不等于唯一答案。')
        if len(retained)>1: limitations.append('多个候选获得保留证据，不能独立定案。')
        if answer is None: limitations.append('缺少唯一候选自身的审阅证据；不由排除或剩余项自动定案。')
        status = 'unsupported_type' if not matches else 'incomplete_input' if not complete else 'reviewed' if answer else 'needs_evidence'
        if q['question_type'] in {'应用文','读后续写'}:
            answer = None
            status = 'needs_evidence' if complete else 'incomplete_input'
            limitations.append('写作入口提供课程约束与动作；完整批改和评分由宿主依独立评分契约完成，本核心不虚构改稿或分数。')
        demo = self.demonstration(matches,candidate_analysis,chain)
        result = {'schema_version':'1.7.0','question_id':q['question_id'],'question_type':q['question_type'],'task_type':q.get('task_type','unknown'),'method_matches':matches,'method_chain':chain,'trigger_evidence':triggers,'evidence_graph':graph.result(q),'candidate_analysis':candidate_analysis,'answer':answer,'answer_confidence':'medium' if answer else 'low','student_symptoms':q.get('student_symptoms',[]),'demonstration':demo,'status':status,'limitations':limitations,'next_action':chain[0]['action'] if chain else '补齐题面并确认受支持题型；不猜答案。','stop_rule':chain[0]['stop_rule'] if chain else '未覆盖题型停止推断。','review_scope':'external_semantic_review' if answer else 'mechanical_structure_only','method_versions':{x['method_id']:self.registry.methods[x['method_id']]['version'] for x in matches},'content_eligible':bool(answer and complete),'difficulty':q.get('difficulty','unknown'),'answer_verification':{'retained_candidates':sorted(retained),'eliminated_candidates':sorted(eliminated),'unresolved_candidates':unresolved,'candidate_coverage_complete':candidate_coverage,'unique_supported_candidate':len(retained)==1,'closed':bool(answer)}}
        result['grammar_navigation']=navigate_grammar(q,self.registry)
        result['execution_trace']=execute_actions(q,chain,matches,self.registry,graph,trigger_nodes,complete,relation_nodes)
        result['demonstration']=self.demonstration(matches,candidate_analysis,chain)
        if result['execution_trace']:
            pending=next((s for s in chain if s['state'] not in {'executed','stopped'}),None)
            last=result['execution_trace'][-1]
            result['next_action']='当前方法已刹车：'+last['stop_rule_check']+'；先解决这个缺口，不消费该步输出。' if last['state']=='stopped' else pending['action'] if pending else '各已提交动作已有产物；继续核所有竞争候选及回填验证，不由分组或剩余项自动定案。'
            result['limitations'].append('动作与产物来自外部审阅；类型、依赖和引文一致不认证真实执行或语义正确。')
            if result['review_scope']=='mechanical_structure_only' and any(x['state']=='produced' for x in result['execution_trace']):
                result['review_scope']='external_action_review'
        if any(x['state']=='produced' and x['output']['kind']=='verification_result' and x['output']['verdict']!='supports' for x in result['execution_trace']):
            result.update(answer=None,answer_confidence='low',content_eligible=False,status='needs_evidence',review_scope='external_action_review')
            result['answer_verification']['closed']=False
            result['limitations'].append('显式回填核验未通过；先解决验证冲突，不沿用此前候选结论。')
        result['writing_feedback']=writing_feedback(q,self.registry,graph,trigger_nodes)
        result['evidence_graph']=graph.result(q)
        result['lesson_feedback']=lesson_feedback(q,result,self.registry,graph,trigger_nodes,relation_nodes)
        if result['lesson_feedback']:
            result['limitations'].extend(result['lesson_feedback']['limitations'])
            if result['lesson_feedback']['scope']=='single_question_lesson': result['review_scope']='external_single_question_lesson'
        result['evidence_graph']=graph.result(q)
        if result['writing_feedback']:
            result['limitations'].extend(result['writing_feedback']['limitations'])
            if result['writing_feedback']['scope']!='unreviewed': result['review_scope']='external_writing_review'
            if result['writing_feedback']['scope']=='full_correction': result['status']='reviewed'
        validate_schema('question-analysis',result)
        validate_execution_trace(result,self.registry)
        validate_lesson_projection(result,self.registry)
        validate_writing_projection(result,self.registry)
        return result

    def demonstration(self,matches,candidates,chain):
        # Transparent heuristic ranking. Never measures teaching success or changes truth.
        verified = sum(x['trigger_verified'] for x in matches)
        values = {'method_clarity':1 if len(chain)==1 else 0.5 if chain else 0,'contrast':1 if len({c['candidate'] for c in candidates})>=2 else 0,'visuality':1 if chain and all(self.registry.methods[x['method_id']]['visual_formula'] for x in chain) else 0,'transferability':0.5 if chain else 0,'trigger_clarity':1 if verified else 0,'evidence_visibility':1 if candidates else 0,'compression':1 if len(chain)<=3 and chain else 0}
        values['score'] = round(sum(values.values())/len(values),3)
        return values

class PaperAnalyzer:
    def __init__(self,analyzer=None): self.analyzer=analyzer or QuestionAnalyzer()
    def analyze(self,paper):
        if set(paper) != {'paper_id','questions'} or not isinstance(paper['questions'],list):
            raise ValueError('Paper requires paper_id and questions')
        if len({q['question_id'] for q in paper['questions']}) != len(paper['questions']):
            raise ValueError('Duplicate question id in paper')
        results = [self.analyzer.analyze(q) for q in paper['questions']]
        counts, difficulty = {}, {}
        for q in results:
            for m in q['method_matches']: counts[m['method_id']]=counts.get(m['method_id'],0)+1
            difficulty[q['difficulty']] = difficulty.get(q['difficulty'],0)+1
        eligible = [q for q in results if q['content_eligible']]
        output = {'schema_version':'1.0.0','paper_id':paper['paper_id'],'questions':results,'recommendations':[q['question_id'] for q in sorted(eligible,key=lambda q:q['demonstration']['score'],reverse=True)],'method_counts':counts,'difficulty_counts':difficulty,'evidence_complete_count':len(eligible),'case_candidates':[q['question_id'] for q in eligible],'limitations':['难度为输入标注，未做统计校准。推荐仅是进入人工课程审阅的候选，不是发布授权。未闭合的题不推荐。']}
        validate_schema('paper-analysis',output)
        return output
