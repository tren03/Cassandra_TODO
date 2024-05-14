import matplotlib
matplotlib.use('Agg')  # Use the 'Agg' backend which doesn't require a display
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
from flask import send_file
from flask import Flask, render_template, request, redirect, url_for
from cassandra.cluster import Cluster
from uuid import uuid4
from collections import defaultdict
import time

app = Flask(__name__)

# Connect to the Cassandra cluster
cluster = Cluster(['127.0.0.1'])  # Replace '127.0.0.1' with your Cassandra node IP
session = cluster.connect()
session.execute("CREATE KEYSPACE IF NOT EXISTS todo WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}")
session.set_keyspace('todo')
session.execute("CREATE TABLE IF NOT EXISTS tasks (id UUID PRIMARY KEY, task TEXT, group_tag TEXT, day TEXT, hour TEXT)")

# Ensure each request has its own Matplotlib instance
def create_plot():
    fig, ax = plt.subplots()
    return fig, ax

def save_plot(fig):
    img_bytes = io.BytesIO()
    fig.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    plt.close(fig)
    return img_bytes

@app.route('/')
def index():
    # Get all tasks
    rows = session.execute("SELECT * FROM tasks")
    tasks = [{'id': row.id, 'task': row.task, 'group': row.group_tag, 'time':row.hour, 'day':row.day} for row in rows]

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
    fig, ax = create_plot()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%')
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle

    # Save the plot to a BytesIO object
    img_bytes = save_plot(fig)

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
    fig, ax = create_plot()
    ax.bar(labels, sizes)
    ax.set_xlabel('Group')
    ax.set_ylabel('Number of Tasks')
    ax.set_title('Number of Tasks in Each Group')

    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # Save the histogram to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the histogram image as a file
    return send_file(img_bytes, mimetype='image/png')


@app.route('/task_hour')
def task_hour():
    # Fetch data from the database
    rows = session.execute("SELECT * FROM tasks")
    task_counts = defaultdict(int)

    for row in rows:
        # Extract hour from the 'hour' field (assuming hour is stored in 'hour:minute' format)
        hour = row.hour.split(':')[0]
        task_counts[hour] += 1

    # Create a histogram
    hours = list(task_counts.keys())
    tasks = list(task_counts.values())

    # Convert hours to integers for proper sorting and plotting
    hours_int = [int(hour) for hour in hours]
    hours_sorted, tasks_sorted = zip(*sorted(zip(hours_int, tasks)))

    fig, ax = create_plot()
    ax.bar(hours_sorted, tasks_sorted)
    ax.set_xlabel('Hour of the Day')
    ax.set_ylabel('Number of Tasks')
    ax.set_title('Number of Tasks by Hour of the Day')

    # Set x-axis ticks to show every hour
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))

    # Ensure integers are displayed for hours on x-axis
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))

    # Set the x-axis limit from 0 to 23 (assuming 24-hour format)
    ax.set_xlim(0, 23)

    # Save the histogram to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the histogram image as a file
    return send_file(img_bytes, mimetype='image/png')


@app.route('/task_month')
def task_month():
    # Fetch data from the database
    rows = session.execute("SELECT * FROM tasks")
    task_counts = defaultdict(int)

    for row in rows:
        # Extract month from the 'day' field (assuming day is stored in 'YYYY-MM-DD' format)
        month = row.day.split('-')[1]
        task_counts[month] += 1

    # Create a histogram
    months = list(task_counts.keys())
    tasks = list(task_counts.values())

    # Convert months to integers for proper sorting and plotting
    months_int = [int(month) for month in months]
    months_sorted, tasks_sorted = zip(*sorted(zip(months_int, tasks)))

    fig, ax = create_plot()
    ax.bar(months_sorted, tasks_sorted)
    ax.set_xlabel('Month')
    ax.set_ylabel('Number of Tasks')
    ax.set_title('Number of Tasks by Month')

    # Set x-axis ticks to show every month
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))

    # Ensure integers are displayed for months on x-axis
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))

    # Save the histogram to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the histogram image as a file
    return send_file(img_bytes, mimetype='image/png')



if __name__ == '__main__':
    app.run(debug=True)



#since matplot lib isnt thread safe, we needed to make each call have its for graph have its own instance. this fixed the problem of graphs not getting generated correctly