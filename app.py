from flask import Flask, render_template, request, redirect, url_for
from cassandra.cluster import Cluster
from uuid import uuid4
from collections import defaultdict
import io
from flask import send_file
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

app = Flask(__name__)

# Connect to the Cassandra cluster
cluster = Cluster(['127.0.0.1'])  # Replace '127.0.0.1' with your Cassandra node IP
session = cluster.connect()
session.execute("CREATE KEYSPACE IF NOT EXISTS todo WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}")
session.set_keyspace('todo')
session.execute("CREATE TABLE IF NOT EXISTS tasks (id UUID PRIMARY KEY, task TEXT, group_tag TEXT, day TEXT, hour TEXT)")


@app.route('/')
def index():
    # Get all tasks
    rows = session.execute("SELECT * FROM tasks")
    tasks = [{'id': row.id, 'task': row.task, 'group': row.group_tag} for row in rows]

    # Extract distinct groups from tasks
    all_groups = [task['group'] for task in tasks]

    # Filter out empty groups
    non_empty_groups = set(group for group in all_groups if group)

    # Get the selected group from the request
    selected_group = request.args.get('group')

    # Filter tasks for the selected group if specified
    if selected_group:
        tasks = [task for task in tasks if task['group'] == selected_group]

    return render_template('index.html', tasks=tasks, groups=non_empty_groups, selected_group=selected_group)


@app.route('/add', methods=['POST'])
def add():
    task = request.form['task']
    group_tag = request.form['group']
    day = request.form.get('day')
    hour = request.form.get('hour')

    if task != "":
        if group_tag == "":
            group_tag = "default"

        # Insert task into the database
        session.execute("INSERT INTO tasks (id, task, group_tag, day, hour) VALUES (%s, %s, %s, %s, %s)",
                        (uuid4(), task, group_tag, day, hour))

    return redirect(url_for('index'))

@app.route('/delete/<uuid:id>')
def delete(id):
    session.execute("DELETE FROM tasks WHERE id = %s", [id])
    return redirect(url_for('index'))

@app.route('/tasks_count_chart')
def tasks_count_chart():
    rows = session.execute("SELECT * FROM tasks")
    task_counts = defaultdict(int)
    for row in rows:
        task_counts[row.group_tag] += 1

    # Create a pie chart
    labels = list(task_counts.keys())
    sizes = list(task_counts.values())
    plt.pie(sizes, labels=labels, autopct='%1.1f%%')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle

    # Save the plot to a BytesIO object
    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)

    # Clear the plot to release memory
    plt.clf()

    # Send the image as a file
    return send_file(img_bytes, mimetype='image/png')

@app.route('/task_histogram')
def task_histogram():
    # Fetch data from the database
    rows = session.execute("SELECT * FROM tasks")
    task_counts = defaultdict(int)
    for row in rows:
        task_counts[row.group_tag] += 1

    # Create a histogram
    labels = list(task_counts.keys())
    sizes = list(task_counts.values())
    fig, ax = plt.subplots()
    ax.bar(labels, sizes)
    ax.set_xlabel('Group')
    ax.set_ylabel('Number of Tasks')
    ax.set_title('Number of Tasks in Each Group')

    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # Save the histogram to a BytesIO object
    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)

    # Clear the plot to release memory
    plt.clf()

    # Send the histogram image as a file
    return send_file(img_bytes, mimetype='image/png')
    
if __name__ == '__main__':
    app.run(debug=True)
