from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.csv_manager import CSVManager
from utils.auth import login_required
from datetime import datetime
import os
import uuid

sns_bp = Blueprint('sns', __name__)

@sns_bp.route('/')
@login_required
def index():
    posts = CSVManager.read('data/sns_posts.csv')
    # Sort posts by timestamp descending
    posts.sort(key=lambda x: x['timestamp'], reverse=True)

    comments = CSVManager.read('data/sns_comments.csv')
    likes = CSVManager.read('data/sns_likes.csv')

    # Attach comments and like status to posts
    for post in posts:
        post['comments'] = [c for c in comments if c['post_id'] == post['id']]
        post['is_liked'] = any(l['post_id'] == post['id'] and l['username'] == session['user']['name'] for l in likes)

    return render_template('sns/index.html', posts=posts)

@sns_bp.route('/post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content')
    image = request.files.get('image')

    image_path = ""
    if image:
        filename = f"{uuid.uuid4()}_{image.filename}"
        image_path = f"uploads/sns/{filename}"
        image.save(os.path.join('static', image_path))

    new_post = {
        'id': str(uuid.uuid4()),
        'author': session['user']['name'],
        'image_path': image_path,
        'content': content,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'likes_count': '0'
    }

    CSVManager.append('data/sns_posts.csv', new_post, ['id', 'author', 'image_path', 'content', 'timestamp', 'likes_count'])
    return redirect(url_for('sns.index'))

@sns_bp.route('/like/<post_id>')
@login_required
def like_post(post_id):
    likes = CSVManager.read('data/sns_likes.csv')
    username = session['user']['name']

    # Check if already liked
    liked = False
    for i, l in enumerate(likes):
        if l['post_id'] == post_id and l['username'] == username:
            likes.pop(i)
            liked = True
            break

    if not liked:
        likes.append({'post_id': post_id, 'username': username})

    CSVManager.write('data/sns_likes.csv', likes, ['post_id', 'username'])

    # Update likes_count in posts
    posts = CSVManager.read('data/sns_posts.csv')
    for p in posts:
        if p['id'] == post_id:
            p['likes_count'] = str(len([l for l in likes if l['post_id'] == post_id]))
            break
    CSVManager.write('data/sns_posts.csv', posts, ['id', 'author', 'image_path', 'content', 'timestamp', 'likes_count'])

    return redirect(url_for('sns.index'))

@sns_bp.route('/comment/<post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content')
    new_comment = {
        'id': str(uuid.uuid4()),
        'post_id': post_id,
        'author': session['user']['name'],
        'content': content,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    CSVManager.append('data/sns_comments.csv', new_comment, ['id', 'post_id', 'author', 'content', 'timestamp'])
    return redirect(url_for('sns.index'))
