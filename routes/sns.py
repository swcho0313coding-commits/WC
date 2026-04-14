from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from utils.auth import login_required, permission_required
from datetime import datetime
import os
import uuid

sns_bp = Blueprint('sns', __name__)

@sns_bp.route('/')
@login_required
@permission_required('post_sns')
def index():
    posts = CSVManager.read('data/sns_posts.csv')
    comments = CSVManager.read('data/sns_comments.csv')

    # Attach comments to posts
    for p in posts:
        p['comments'] = [c for c in comments if c['post_id'] == p['id']]

    # Priority Logic: Higher grades first, then timestamp
    grade_ranks = {}
    ranks_data = CSVManager.read('data/grades.csv')
    for r in ranks_data:
        grade_ranks[r['name']] = int(r['rank'])

    def sort_key(post):
        rank = grade_ranks.get(post['grade'], 99)
        return (rank, post['timestamp'])

    sorted_posts = sorted(posts, key=sort_key)

    return render_template('sns/index.html', posts=sorted_posts)

@sns_bp.route('/post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content')
    file = request.files.get('file')

    file_path = ""
    if file:
        filename = f"{uuid.uuid4()}_{file.filename}"
        os.makedirs('static/uploads/sns', exist_ok=True)
        file.save(os.path.join('static/uploads/sns', filename))
        file_path = f"uploads/sns/{filename}"

    new_post = {
        'id': str(uuid.uuid4()),
        'user': session['user']['name'],
        'grade': session['user']['grade'],
        'content': content,
        'image': file_path,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'likes': '0'
    }

    CSVManager.append('data/sns_posts.csv', new_post, ['id', 'user', 'grade', 'content', 'image', 'timestamp', 'likes'])
    flash("게시물이 등록되었습니다.")
    return redirect(url_for('sns.index'))

@sns_bp.route('/like/<post_id>')
@login_required
def like(post_id):
    posts = CSVManager.read('data/sns_posts.csv')
    for p in posts:
        if p['id'] == post_id:
            # Check if user already liked (simplified: allow multiple for now as per "SF/Modern" fun, or just toggle)
            p['likes'] = str(int(p['likes']) + 1)
            break
    CSVManager.write('data/sns_posts.csv', posts, ['id', 'user', 'grade', 'content', 'image', 'timestamp', 'likes'])
    return redirect(url_for('sns.index'))

@sns_bp.route('/comment/<post_id>', methods=['POST'])
@login_required
def comment(post_id):
    content = request.form.get('content')
    new_comment = {
        'post_id': post_id,
        'user': session['user']['name'],
        'grade': session['user']['grade'],
        'content': content,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    CSVManager.append('data/sns_comments.csv', new_comment, ['post_id', 'user', 'grade', 'content', 'timestamp'])
    return redirect(url_for('sns.index'))
