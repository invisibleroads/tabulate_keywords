import datetime
import numpy as np
import requests
from argparse import ArgumentParser
from bs4 import BeautifulSoup
from os.path import basename, join
from invisibleroads_macros.text import compact_whitespace
from pandas import DataFrame
from tempfile import mkdtemp


class ToolError(Exception):
    pass


def run(
        target_folder,
        journal_names, text_terms, mesh_terms, custom_expression,
        author_names, from_date, to_date, date_interval_in_years):
    log_path = join(target_folder, 'search_counts.log')
    log_file = open(log_path, 'wt')

    date_ranges = get_date_ranges(from_date, to_date, date_interval_in_years)
    
    if author_names:
        array = np.zeros((len(author_names), 1))
        for author_index, author_name in enumerate(author_names):
            author_expression = get_expression(author_name, from_date, to_date)
            author_search_count = get_search_count(author_expression)
            log_search_count(
                    log_file, author_expression, author_search_count)
             
            array[ author_index, 1] = author_search_count
        
        table = DataFrame(array, index=[author_names], columns=['articles_count'])
        table_path = join(target_folder, 'search_counts.csv')
        table.to_csv(table_path)
        print('log_path = %s' % log_path)
        print('table_path = %s' % table_path)
        return dict()


        
    else:
        array = np.zeros((len(date_ranges), len(journal_names)))
        partial_expression = get_expression(
            text_terms=text_terms, mesh_terms=mesh_terms,
            custom_expression=custom_expression)
        selected_search_count = 0
        total_search_count = 0

        for date_range_index, (date_a, date_b) in enumerate(date_ranges):
            for journal_index, journal_name in enumerate(journal_names):
                # Get selected_search_count
                journal_selected_expression = get_expression(
                    journal_name, from_date=date_a, to_date=date_b,
                    custom_expression=partial_expression)
                journal_selected_search_count = get_search_count(
                    journal_selected_expression)
                log_search_count(
                    log_file, journal_selected_expression,
                    journal_selected_search_count)
                # Get total_search_count
                journal_total_expression = get_expression(
                    journal_name, from_date=date_a, to_date=date_b)
                journal_total_search_count = get_search_count(
                    journal_total_expression)
                log_search_count(
                    log_file, journal_total_expression,
                    journal_total_search_count)
                # Save
                try:
                    array[
                        date_range_index, journal_index,
                    ] = journal_selected_search_count / float(
                        journal_total_search_count)
                except ZeroDivisionError:
                    pass
                selected_search_count += journal_selected_search_count
                total_search_count += journal_total_search_count
        table = DataFrame(array, index=[
            date_a.year for date_a, date_b in date_ranges
        ], columns=[
            journal_names
        ])
        table_path = join(target_folder, 'search_counts.csv')
        table.to_csv(table_path)

        axes = (table * 100).plot()
        axes.set_ylabel('%')
        axes.set_xlabel('Year')
        axes.set_title('Percent frequency over time')
        figure = axes.get_figure()
        figure_path = join(target_folder, 'search_counts.png')
        figure.savefig(figure_path)
        print('log_path = %s' % log_path)
        print('table_path = %s' % table_path)
        print('figure_path = %s' % figure_path)
        return dict(
            image_name=basename(figure_path),
            selected_search_count=selected_search_count,
            total_search_count=total_search_count)


def get_expression(
        journal_name=None, text_terms=None, mesh_terms=None,
        from_date=None, to_date=None, custom_expression=None, author_name=None):
    expression_parts = []
    if journal_name:
        expression_parts.append('"%s"[Journal]' % journal_name)
    if text_terms or mesh_terms:
        terms = []
        terms.extend('"%s"[Text Word]' % x for x in text_terms or [])
        terms.extend('"%s"[MeSH Terms]' % x for x in mesh_terms or [])
        expression_parts.append(' OR '.join(terms))
    if custom_expression:
        expression_parts.append(custom_expression)
    if author_name:
        expression_parts.append('"%s"[Author]' % author_name)
    if from_date:
        from_date_string = from_date.strftime(
            '%Y/%m/%d')
        to_date_string = to_date.strftime(
            '%Y/%m/%d') if to_date else '3000'
        expression_parts.append(
            '"%s"[Date - Publication] : "%s"[Date - Publication]' % (
                from_date_string, to_date_string))
    if len(expression_parts) <= 1:
        expression = ''.join(expression_parts)
    else:
        expression = '(%s)' % ') AND ('.join(expression_parts)
    return compact_whitespace(expression)


def get_date_ranges(from_date, to_date, interval_in_years):
    if from_date and to_date and from_date > to_date:
        raise ToolError('invalid_date_range')
    date_ranges = []
    date_b = from_date - datetime.timedelta(days=1)
    while date_b < to_date:
        date_a = date_b + datetime.timedelta(days=1)
        date_b = datetime.datetime(
            date_a.year + interval_in_years, date_a.month, date_a.day,
        ) - datetime.timedelta(days=1)
        if date_b > to_date:
            date_b = to_date
        date_ranges.append((date_a, date_b))
    return date_ranges


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


def load_unique_lines(source_path):
    source_text = open(source_path, 'rt').read().strip()
    return sorted(set([x.strip() for x in source_text.splitlines()]))


def parse_date(string):
    return datetime.datetime.strptime(string, '%m/%d/%Y')


if __name__ == '__main__':
    argument_parser = ArgumentParser()
    argument_parser.add_argument(
        '--journal_names_path',
        type=load_unique_lines, dest='journal_names',
        metavar='PATH')
    argument_parser.add_argument(
        '--author_names_path',
        type=load_unique_lines, dest='author_names',
        metavar='PATH')
    argument_parser.add_argument(
        '--text_terms_path',
        type=load_unique_lines, dest='text_terms',
        metavar='PATH')
    argument_parser.add_argument(
        '--mesh_terms_path',
        type=load_unique_lines, dest='mesh_terms',
        metavar='PATH')
    argument_parser.add_argument(
        '--custom_expression',
        metavar='EXPRESSION')
    argument_parser.add_argument(
        '--from_date', type=parse_date,
        metavar='DATE')
    argument_parser.add_argument(
        '--to_date', type=parse_date,
        metavar='DATE')
    argument_parser.add_argument(
        '--date_interval_in_years',
        type=int,
        metavar='INTEGER')
    args = argument_parser.parse_args()
    target_folder = mkdtemp()
    result_properties = run(
        target_folder,
        args.journal_names, args.text_terms, args.mesh_terms,
        args.custom_expression, args.author_names, args.from_date, args.to_date,
        args.date_interval_in_years)
    print(result_properties)
