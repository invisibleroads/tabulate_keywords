import numpy as np

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, send_from_directory

from invisibleroads_macros import disk
from os.path import join
from pandas import DataFrame

from joblib import Parallel, delayed

app = Flask(__name__)
results_folder = disk.make_folder('results')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/run', methods=['GET', 'POST'])
def run():
    journals = sorted(set(request.form['journals'].splitlines()))
    journal_count = len(journals)
    #set journals in order, ensure only one instance of each journal
    
    key_val = sorted(set(request.form['key_val'].splitlines()))[0]
    #temporary
    #key_val = 'Text Word'
    
    keywords = sorted(set(request.form['keywords'].splitlines()))
    #keyword_count = len(keywords)

    
    date_from = sorted(set(request.form['from'].splitlines()))[0]
    date_to =  sorted(set(request.form['to'].splitlines()))[0]

    date_from = '%s/%s/%s' %(date_from[6:10], date_from[0:2], date_from[3:5])
    date_to = '%s/%s/%s' %(date_to[6:10], date_to[0:2], date_to[3:5])



    array = np.zeros((journal_count, 1), dtype=np.uint64)
    journal_total_counts = []

    log_path = join(results_folder, 'log.txt')
    log_file = open(log_path, 'wt')
    for journal_index, journal in enumerate(journals):
        #for keyword_index, keyword in enumerate(keywords):
        expression = get_expression(journal,date_from, date_to, key_val, keywords)
        journal_keyword_result_count = get_result_count(expression)
        
        array[journal_index, 0] = journal_keyword_result_count
        
        log_file.write(expression + '\n')
        log_file.write(str(journal_keyword_result_count) + '\n\n')
        
        
        journal_result_count = get_result_count('"%s"[Journal]' % journal)
        journal_total_counts.append(journal_result_count)
    log_file.close()

    table = DataFrame(array, columns=['||'.join(' %s ' % keyword for keyword in keywords)], index=journals)
    journal_selected_counts = table.sum(axis=1)
    journal_selected_percents = 100 * (
        journal_selected_counts / journal_total_counts)
    table['journal_selected_percent'] = journal_selected_percents
    table['journal_total_count'] = journal_total_counts
    table_path = join(results_folder, 'response.csv')
    table.to_csv(table_path)
    return render_template(
        'response.html',
        journal_packs=zip(journals, journal_selected_percents))


@app.route('/results.zip')
def download():
    archive_path = results_folder + '.zip'
    disk.compress(results_folder, archive_path)
    return send_from_directory('.', filename=archive_path)


def get_expression(journal, date_from, date_to, key_val, keywords):
    positive_expression = '"%s"[Journal] AND ("%s"[%s]' % (
        journal, keywords[0], key_val)
    optional_keywords = list(keywords)
    optional_keywords.remove(keywords[0])

    optional_expression = ''
    for x in optional_keywords:
        optional_expression += ' OR "%s"[%s]' %(x,key_val)

    dates = 'AND ("%s"[PDAT]: "%s"[PDAT])' % (date_from, date_to)
    return positive_expression + optional_expression + ') ' + dates

def get_result_count(expression):
    url = 'http://www.ncbi.nlm.nih.gov/pubmed/'
    response = requests.get(url, params=dict(term=expression))
    soup = BeautifulSoup(response.text)
    return int(soup.find(id='resultcount')['value'])


if __name__ == '__main__':
    app.run(port=18927, debug=True)
