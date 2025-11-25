from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, flash
import os
from pathlib import Path
from werkzeug.utils import secure_filename
import logging
from juba_checker import CredentialChecker, ProxyManager
from threading import Thread
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'juba_checker_secret_key_change_in_production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

processing_status = {}


def allowed_file(filename):
    return filename.endswith('.txt')


def process_files_background(upload_folder, output_folder, workers, proxy_file, job_id):
    try:
        processing_status[job_id] = {'status': 'running', 'progress': 0, 'message': 'Starting...'}
        
        proxy_manager = ProxyManager(proxy_file) if proxy_file and os.path.exists(proxy_file) else None
        checker = CredentialChecker(proxy_manager=proxy_manager)
        
        processing_status[job_id]['message'] = 'Processing credentials...'
        checker.process_folder(upload_folder, output_folder, workers, dry_run=False)
        
        processing_status[job_id] = {'status': 'completed', 'progress': 100, 'message': 'Processing complete!'}
    except Exception as e:
        logger.error(f"Background processing error: {e}")
        processing_status[job_id] = {'status': 'error', 'progress': 0, 'message': str(e)}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        flash('No files selected')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files[]')
    proxy_file = request.files.get('proxy_file')
    workers = int(request.form.get('workers', 10))
    
    job_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    upload_path = Path(app.config['UPLOAD_FOLDER']) / job_id
    upload_path.mkdir(parents=True, exist_ok=True)
    
    uploaded_files = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if not filename.startswith('search_'):
                filename = 'search_' + filename
            file_path = upload_path / filename
            file.save(str(file_path))
            uploaded_files.append(filename)
    
    proxy_path = None
    if proxy_file and proxy_file.filename:
        proxy_filename = secure_filename(proxy_file.filename)
        proxy_path = upload_path / proxy_filename
        proxy_file.save(str(proxy_path))
    
    if not uploaded_files:
        flash('No valid files uploaded')
        return redirect(url_for('index'))
    
    output_path = Path(app.config['RESULTS_FOLDER']) / job_id
    output_path.mkdir(parents=True, exist_ok=True)
    
    thread = Thread(target=process_files_background, args=(str(upload_path), str(output_path), workers, str(proxy_path) if proxy_path else None, job_id))
    thread.daemon = True
    thread.start()
    
    flash(f'Processing started! Job ID: {job_id}')
    return redirect(url_for('results', job_id=job_id))


@app.route('/results/<job_id>')
def results(job_id):
    results_path = Path(app.config['RESULTS_FOLDER']) / job_id
    
    status = processing_status.get(job_id, {'status': 'unknown', 'progress': 0, 'message': 'No status available'})
    
    domain_results = {}
    if results_path.exists():
        for domain_folder in results_path.iterdir():
            if domain_folder.is_dir():
                result_file = domain_folder / 'results.txt'
                if result_file.exists():
                    with open(result_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    domain_results[domain_folder.name] = {
                        'count': len(lines),
                        'file': str(result_file.relative_to(app.config['RESULTS_FOLDER']))
                    }
    
    return render_template('results.html', job_id=job_id, status=status, domain_results=domain_results)


@app.route('/status/<job_id>')
def get_status(job_id):
    status = processing_status.get(job_id, {'status': 'unknown', 'progress': 0, 'message': 'No status available'})
    return jsonify(status)


@app.route('/download/<path:filepath>')
def download_file(filepath):
    file_path = Path(app.config['RESULTS_FOLDER']) / filepath
    if file_path.exists() and file_path.is_file():
        return send_file(str(file_path), as_attachment=True)
    return "File not found", 404


@app.route('/jobs')
def list_jobs():
    results_path = Path(app.config['RESULTS_FOLDER'])
    jobs = []
    
    if results_path.exists():
        for job_folder in sorted(results_path.iterdir(), reverse=True):
            if job_folder.is_dir():
                job_id = job_folder.name
                status = processing_status.get(job_id, {'status': 'completed', 'progress': 100, 'message': 'Completed'})
                
                domain_count = sum(1 for d in job_folder.iterdir() if d.is_dir())
                
                jobs.append({
                    'job_id': job_id,
                    'status': status['status'],
                    'domain_count': domain_count
                })
    
    return render_template('jobs.html', jobs=jobs)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
