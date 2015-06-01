import numpy as np

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, send_from_directory


from invisibleroads_macros import disk
from os.path import join
from pandas import DataFrame


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

    keywords = sorted(set(request.form['keywords'].splitlines()))
    keyword_count = len(keywords)
    array = np.zeros((journal_count, keyword_count), dtype=np.uint64)
    journal_total_counts = []

    log_path = join(results_folder, 'log.txt')
    log_file = open(log_path, 'wt')
    for journal_index, journal in enumerate(journals):
        for keyword_index, keyword in enumerate(keywords):
            expression = get_expression(journal, keyword, keywords)
            journal_keyword_result_count = get_result_count(expression)
            array[journal_index, keyword_index] = journal_keyword_result_count
            log_file.write(expression + '\n')
            log_file.write(str(journal_keyword_result_count) + '\n\n')
        journal_result_count = get_result_count('"%s"[Journal]' % journal)
        journal_total_counts.append(journal_result_count)
    log_file.close()

    table = DataFrame(array, columns=keywords, index=journals)
    journal_selected_counts = table.sum(axis=1)
    journal_selected_percents = 100 * (
        journal_selected_counts / journal_total_counts)
    table['journal_selected_percent'] = journal_selected_percents
    table['journal_selected_count'] = journal_selected_counts
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


def get_expression(journal, keyword, keywords):
    positive_expression = '(("%s"[Journal]) AND %s[Text Word])' % (
        journal, keyword)
    optional_keywords = list(keywords)
    optional_keywords.remove(keyword)
    optional_expression = ' '.join(
        'OR "%s"[Text Word]' % x for x in optional_keywords)
    return positive_expression + ' ' + optional_expression


def get_result_count(expression):
    url = 'http://www.ncbi.nlm.nih.gov/pubmed/'
    response = requests.get(url, params=dict(term=expression))
    soup = BeautifulSoup(response.text)
    return int(soup.find(id='resultcount')['value'])


if __name__ == '__main__':
    app.run(port=18927)
