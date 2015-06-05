import datetime
import requests
from argparse import ArgumentParser
from bs4 import BeautifulSoup
from os.path import join
from pandas import DataFrame
from tempfile import mkdtemp


def run(
        target_folder, journal_names, text_terms, mesh_terms,
        from_date, to_date):
    log_path = join(target_folder, 'search_counts.log')
    log_file = open(log_path, 'wt')
    journal_selected_search_counts, journal_total_search_counts = [], []
    for journal_name in journal_names:
        # Get selected_search_count
        journal_selected_expression = get_expression(
            journal_name, text_terms, mesh_terms, from_date, to_date)
        journal_selected_search_count = get_search_count(
            journal_selected_expression)
        log_search_count(
            log_file, journal_selected_expression,
            journal_selected_search_count)
        # Get total_search_count
        journal_total_expression = get_expression(
            journal_name)
        journal_total_search_count = get_search_count(
            journal_total_expression)
        log_search_count(
            log_file, journal_total_expression,
            journal_total_search_count)
        # Append
        journal_selected_search_counts.append(journal_selected_search_count)
        journal_total_search_counts.append(journal_total_search_count)
    table = get_table(
        journal_selected_search_counts, journal_total_search_counts,
        journal_names)
    table_path = join(target_folder, 'search_counts.csv')
    table.to_csv(table_path, index=False)
    print('log_path = %s' % log_path)
    print('table_path = %s' % table_path)
    return dict(
        search_fraction_by_journal_name=dict(zip(
            journal_names, table['selected_search_fraction'])))


def get_expression(
        journal_name, text_terms=None, mesh_terms=None,
        from_date=None, to_date=None):
    expression_parts = []
    # Add journal
    journal_expression = '"%s"[Journal]' % journal_name
    expression_parts.append(journal_expression)
    # Add terms
    terms = []
    terms.extend('"%s"[Text Word]' % x for x in text_terms or [])
    terms.extend('"%s"[MeSH Terms]' % x for x in mesh_terms or [])
    if terms:
        expression_parts.append('(%s)' % ' OR '.join(terms))
    # Add dates
    if from_date:
        from_date_string = from_date.strftime('%m/%d/%Y')
        to_date_string = to_date.strftime('%m/%d/%Y') if to_date else '3000'
        expression_parts.append('("%s"[PDAT]:"%s"[PDAT])' % (
            from_date_string, to_date_string))
    return ' AND '.join(expression_parts)


def get_search_count(expression):
    url = 'http://www.ncbi.nlm.nih.gov/pubmed/'
    response = requests.get(url, params=dict(term=expression))
    soup = BeautifulSoup(response.text)
    return int(soup.find(id='resultcount')['value'])


def log_search_count(log_file, expression, search_count):
    print(expression)
    print(search_count)
    log_file.write(expression + '\n')
    log_file.write(str(search_count) + '\n\n')


def get_table(selected_search_counts, total_search_counts, journal_names):
    table = DataFrame(dict(
        journal_name=journal_names,
        selected_search_count=selected_search_counts,
        total_search_count=total_search_counts))
    table['selected_search_fraction'] = (
        table['selected_search_count'] / table['total_search_count'])
    return table


def load_unique_lines(source_path):
    source_text = open(source_path, 'rt').read().strip()
    return sorted(set([x.strip() for x in source_text.splitlines()]))


def parse_date(string):
    return datetime.datetime.strptime(string, '%m/%d/%Y').date()


if __name__ == '__main__':
    argument_parser = ArgumentParser()
    argument_parser.add_argument(
        '--journal_names_path', type=load_unique_lines, dest='journal_names',
        required=True)
    argument_parser.add_argument(
        '--text_terms_path', type=load_unique_lines, dest='text_terms')
    argument_parser.add_argument(
        '--mesh_terms_path', type=load_unique_lines, dest='mesh_terms')
    argument_parser.add_argument(
        '--from_date', type=parse_date)
    argument_parser.add_argument(
        '--to_date', type=parse_date)
    args = argument_parser.parse_args()
    target_folder = mkdtemp()
    result_properties = run(
        target_folder,
        args.journal_names, args.text_terms, args.mesh_terms,
        args.from_date, args.to_date)
    print(result_properties)
