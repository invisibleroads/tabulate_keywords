import datetime
import shutil
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
    author_names = sorted(set(
        request.form.get('author_names', '').splitlines()))
    text_terms = sorted(set(
        request.form.get('text_terms', '').splitlines()))
    mesh_terms = sorted(set(
        request.form.get('mesh_terms', '').splitlines()))
    custom_expression = request.form.get('custom_expression', '')
    try:
        from_date = parse_date(request.form.get('from_date'))
        to_date = parse_date(request.form.get('to_date'))
    except (TypeError, ValueError):
        from_date, to_date = None, None
    if request.form.get('date_interval_in_years') is not None:
        date_interval_in_years = int(
            request.form.get('date_interval_in_years'))
    else:
        date_interval_in_years = None
    result_properties = run_script(
        target_folder, journal_names, text_terms, mesh_terms,
        custom_expression, author_names, from_date,
        to_date, date_interval_in_years)

    timestamp = datetime.datetime.now().strftime('%Y%m%d-%M%H')
    archive_nickname = '%s-%s' % (
        timestamp, security.make_random_string(16))
    archive_path = join(results_folder, archive_nickname + '.zip')
    disk.compress(target_folder, archive_path)
    
    if 'image_name' in result_properties:
        source_image_path = join(target_folder, result_properties['image_name'])
        target_image_path = join(results_folder, archive_nickname + '.png')
        shutil.copy(source_image_path, target_image_path)

        return render_template(
            'response.html',
            archive_name=basename(archive_path),
            image_name=basename(target_image_path),
            result_properties=result_properties)
    else:
        return render_template('author_response.html', 
                archive_name=basename(archive_path),
                result_properties=result_properties)

@app.route('/download/<file_name>')
def download(file_name):
    file_path = join(results_folder, basename(file_name))
    return send_from_directory('.', filename=file_path)


if __name__ == '__main__':
    app.run( port=27973)
