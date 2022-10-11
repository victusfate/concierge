from rsyslog_cee import log

import spacy
from spacy import displacy

# nlp = spacy.load('en_core_web_sm')
nlp = spacy.load('en_core_web_trf')

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
        'is_stop': token.is_stop 
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


  def line_processor(text):
    global nlp
    doc = nlp(text)

    result = {}  
    # segmenter
    segmenter_results = []
    for sentence in doc.sents:
      segmenter_results.append({
        'text': sentence.text,
        'start': sentence.start_char, 
        'end': sentence.end_char
      })
    log.info('Transformers.line_processor',{'text': text,'segmenter_results': segmenter_results})  
    result['seg'] = segmenter_results

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
        'is_stop': token.is_stop 
      })  
    log.info('Transformers.line_processor',{'text': text,'pos_results': pos_results})
    result['pos'] = pos_results

    # ner
    ner_results = []
    for ent in doc.ents:
      ner_results.append({'text': ent.text, 'start_char': ent.start_char, 'end_char': ent.end_char, 'label': ent.label_ })
    log.info('Transformers.line_processor',{'text': text,'ner_results': ner_results})
    result['ner'] = ner_results

    log.oLogger.summary('server.line_processor.Summary')
    return result

  def splitter(text):
    return Transformers.line_processor(text)