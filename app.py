from flask import Flask, render_template, request, redirect, url_for
from cassandra.cluster import Cluster
from uuid import uuid4

app = Flask(__name__)

# Connect to the Cassandra cluster
cluster = Cluster(['127.0.0.1'])  # Replace '127.0.0.1' with your Cassandra node IP
session = cluster.connect()
session.execute("CREATE KEYSPACE IF NOT EXISTS todo WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}")
session.set_keyspace('todo')
session.execute("CREATE TABLE IF NOT EXISTS tasks (id UUID PRIMARY KEY, task TEXT, group_tag TEXT)")


@app.route('/')
def index():
    # Get all distinct groups
    # there was an error in selection of distinct groups from original table   

    # Get tasks for the selected group (or all tasks if no group is selected)
    selected_group = request.args.get('group')
    if selected_group:
        rows = session.execute("SELECT * FROM tasks WHERE group_tag = %s ALLOW FILTERING", [selected_group])
    else:
        rows = session.execute("SELECT * FROM tasks")

    tasks = [{'id': row.id, 'task': row.task, 'group': row.group_tag} for row in rows]

    # Remove empty groups
    non_empty_groups = set(task['group'] for task in tasks)

    return render_template('index.html', tasks=tasks, groups=non_empty_groups, selected_group=selected_group)


@app.route('/add', methods=['POST'])
def add():
    task = request.form['task']
    group_tag = request.form['group']

    if group_tag == "":
        group_tag = "default"

    # Insert task into the database
    session.execute("INSERT INTO tasks (id, task, group_tag) VALUES (%s, %s, %s)", (uuid4(), task, group_tag))

    # Update group tags table
    # session.execute("INSERT INTO group_tags (group_tag) VALUES (%s) IF NOT EXISTS", [group_tag])

    return redirect(url_for('index'))

@app.route('/delete/<uuid:id>')
def delete(id):
    session.execute("DELETE FROM tasks WHERE id = %s", [id])
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
