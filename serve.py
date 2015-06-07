import datetime
from flask import Flask, render_template, request, send_from_directory
from invisibleroads_macros import disk, security
from os.path import basename, join
from tempfile import mkdtemp

from run import parse_date
from run import run as run_script


app = Flask(__name__)
results_folder = disk.make_folder('results')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/run', methods=['GET', 'POST'])
def run():
    target_folder = mkdtemp()
    journal_names = sorted(set(
        request.form.get('journal_names', '').splitlines()))
    text_terms = sorted(set(
        request.form.get('text_terms', '').splitlines()))
    mesh_terms = sorted(set(
        request.form.get('mesh_terms', '').splitlines()))
    try:
        from_date = parse_date(request.form.get('from_date'))
        to_date = parse_date(request.form.get('to_date'))
    except (TypeError, ValueError):
        from_date, to_date = None, None
    result_properties = run_script(
        target_folder, journal_names, text_terms, mesh_terms,
        from_date, to_date)

    timestamp = datetime.datetime.now().strftime('%Y%m%d-%M%H')
    archive_name = '%s-%s.zip' % (
        timestamp, security.make_random_string(16))
    archive_path = join(results_folder, archive_name)
    disk.compress(target_folder, archive_path)

    return render_template(
        'response.html', archive_name=archive_name, **result_properties)


@app.route('/download/<archive_name>')
def download(archive_name):
    archive_path = join(results_folder, basename(archive_name))
    return send_from_directory('.', filename=archive_path)


if __name__ == '__main__':
    app.run(port=18927, debug=True)
