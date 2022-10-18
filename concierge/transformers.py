from rsyslog_cee import log

import spacy
from spacy import displacy

nlp = spacy.load('en_core_web_sm')
# nlp = spacy.load('en_core_web_trf')

class Transformers:

  def ner(text):
    global nlp
    doc = nlp(text)
    results = []
    for ent in doc.ents:
      results.append({'text': ent.text, 'start_char': ent.start_char, 'end_char': ent.end_char, 'label': ent.label_ })
    log.info('Transformers.ner',{'text': text,'results': results})
    return results

  def pos(text):
    global nlp
    doc = nlp(text)
    results = []
    for token in doc:
      results.append({
        'text': token.text,
        'lemma': token.lemma_, 
        'pos': token.pos_, 
        'tag': token.tag_, 
        'dep': token.dep_,
        'shape': token.shape_, 
        'is_alpha': token.is_alpha, 
        'is_stop': token.is_stop,
        'start_char': token.idx,
        'end_char': token.idx + len(token.text) - 1
      })  
    log.info('Transformers.pos',{'text': text,'results': results})
    return results

  def seg(text):
    global nlp
    doc = nlp(text)
    results = []
    for sentence in doc.sents:
      results.append({
        'text': sentence.text,
        'start': sentence.start_char, 
        'end': sentence.end_char
      })
    log.info('Transformers.seg',{'text': text,'results': results})
    return results

  def ner_pos(text):
    global nlp
    doc = nlp(text)

    result = {}  

    # pos
    pos_results = []
    for token in doc:
      pos_results.append({
        'text': token.text,
        'lemma': token.lemma_, 
        'pos': token.pos_, 
        'tag': token.tag_, 
        'dep': token.dep_,
        'shape': token.shape_, 
        'is_alpha': token.is_alpha, 
        'is_stop': token.is_stop,
        'start_char': token.idx,
        'end_char': token.idx + len(token.text) - 1
      })  
    log.info('Transformers.line_processor',{'text': text,'pos_results': pos_results})
    result['pos'] = pos_results

    # ner
    ner_results = []
    for ent in doc.ents:
      ner_results.append({'text': ent.text, 'start_char': ent.start_char, 'end_char': ent.end_char, 'label': ent.label_ })
    log.info('Transformers.line_processor',{'text': text,'ner_results': ner_results})
    result['ner'] = ner_results
    return result
