#!/usr/bin/env python
""" This script allows to bulk results from we page to sqlite database """
import re
import sqlite3
import string
from os.path import exists
from os import remove
from urllib.request import urlopen
from urllib.parse import urljoin
from lxml import html

CREATE_TASK_TABLE = '''
CREATE TABLE IF NOT EXISTS tasks ( 
    id INTEGER PRIMARY KEY,
    nb INTEGER NOT NULL,
    code TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    weight INTEGER NOT NULL
)
'''

INSERT_TASK = '''
INSERT OR REPLACE INTO tasks (
    nb,
    code,
    description,
    status,
    weight)
    values ( ?, ?, ?, ?, ?)
'''

CREATE_COMP_TABLE = '''
CREATE TABLE IF NOT EXISTS competitors ( 
    competitorid INTEGER NOT NULL,
    competitorname TEXT NOT NULL,
    affiliation TEXT NOT NULL
)
'''

INSERT_COMPETITOR = '''
INSERT OR REPLACE INTO competitors (
    competitorid,
    competitorname,
    affiliation)
    values ( ?, ?, ?)
'''

CREATE_RESULTS_TABLE = '''
CREATE TABLE IF NOT EXISTS results ( 
    RESULT_ID INTEGER PRIMARY KEY,
    COMPETITOR_ID INTEGER NOT NULL,
    TASK_ID INTEGER NOT NULL,
    PERFORMANCE INTEGER NOT NULL,
    PERFORMANCEPENALTY INTEGER NOT NULL,
    RESULT INTEGER NOT NULL,
    POINTS INTEGER NOT NULL,
    TASKPENALTY INTEGER NOT NULL,
    COMPETITIONPENALTY INTEGER NOT NULL,
    SCORE INTEGER NOT NULL,
    NOTES TEXT,
    FOREIGN KEY(COMPETITOR_ID) REFERENCES competitors(competitorid)
    FOREIGN KEY(TASK_ID) REFERENCES tasks(id)
)
'''

INSERT_RESULT = '''
INSERT OR REPLACE INTO results (
    COMPETITOR_ID,
    TASK_ID,
    PERFORMANCE,
    PERFORMANCEPENALTY,
    RESULT,
    POINTS,
    TASKPENALTY,
    COMPETITIONPENALTY,
    SCORE,
    NOTES)
    values ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
'''

CREATE_VIEW_LAST_TASKS = '''
CREATE VIEW IF NOT EXISTS v_last_task_version_ids AS
SELECT
    id TaskID,
    nb TaskNumber,
    code TaskCode,
    description TaskDesc,
    status Status,
    max( weight ) maxWeight
FROM
    tasks
GROUP BY
    nb;
'''

class TaskResult:
    """ Class to store task results """
    def __init__(self, data_node):
        self.rank = data_node['rank']
        self.comp_id = data_node['competitorid']
        self.comp_name = data_node['competitorname']
        self.country = data_node['affiliation']
        self.perf = data_node['performance']
        self.perf_pen = data_node['performancepenalty']
        self.result = data_node['result']
        self.points = data_node['points']
        self.task_pen = data_node['taskpenalty']
        self.comp_pen = data_node['competitionpenalty']
        self.score = data_node['score']
        self.notes = data_node['notes']

    def __str__(self):
        """ Convert to string """
        fields = [self.rank, self.comp_id, self.comp_name, self.country,
            self.perf, self.perf_pen, self.result,
            self.points, self.task_pen, self.comp_pen, self.score,
            self.notes
        ]
        fields_str = [str(x) for x in fields]
        return ' ; '.join(fields_str)

def remove_funny(input_str):
    """ Remove funny chars """
    printable = set(string.printable)
    ret = ''.join(list(filter(lambda x: x in printable, input_str)))
    return ret

def parse_field(node, field_name, append_to_bracket=''):
    """ Parse field """
    result = node.xpath(f'./td[@class="{field_name}"]{append_to_bracket}/text()')
    add_br_tags = node.xpath(f'./td[@class="{field_name}"]{append_to_bracket}//br')
    if result:
        result_to_return = remove_funny(result[0])
        if add_br_tags:
            for add_text in add_br_tags:
                result_to_return += f'{add_text.tail} '
        return result_to_return
    return ''

class CompetitorParser:
    """ Parser for the competitors """
    def __init__(self, database, task_url):
        self.database = database
        self.competitor_list = []
        the_page = html_from_url(task_url)
        competitors = the_page.xpath('//td[@class="competitorid"]/parent::*')
        for competitor in competitors:
            competitor_id = parse_field(competitor, 'competitorid')
            competitor_name = parse_field(competitor, 'competitorname', '/a')
            affiliation = parse_field(competitor, 'affiliation')
            self.competitor_list.append([competitor_id, competitor_name, affiliation])

    def save_to_db(self):
        """ Bulk information to DB """
        self.database.execute(CREATE_COMP_TABLE)
        the_cursor = self.database.cursor()
        for competitor in self.competitor_list:
            comp_number = competitor[0]
            what_to_insert_here = (int(comp_number), str(competitor[1]), str(competitor[2]))
            the_cursor.execute(INSERT_COMPETITOR, what_to_insert_here)
        self.database.commit()

class TaskParser:
    """ Parser for the tasks """
    def __init__(self, database, task_id, task_url):
        self.database = database
        self.database.execute(CREATE_RESULTS_TABLE)
        the_cursor = self.database.cursor()
        the_page = html_from_url(task_url)
        results = the_page.xpath('//td[@class="competitorid"]/parent::*')
        for result in results:
            the_cursor.execute(
                INSERT_RESULT,
                (
                    parse_field(result, 'competitorid'),
                    task_id,
                    parse_field(result, 'performance'),
                    parse_field(result, 'performancepenalty'),
                    parse_field(result, 'result'),
                    parse_field(result, 'points'),
                    parse_field(result, 'taskpenalty'),
                    parse_field(result, 'competitionpenalty'),
                    parse_field(result, 'score'),
                    parse_field(result, 'notes')
                )
            )
        self.database.commit()

class Task:
    """ All the fields for a task """
    def __init__(self, database, task_number, task_code, task_description):
        self.database = database
        self.task_number = task_number
        self.task_code = task_code
        self.task_description = task_description
        self.result_url = {}

    @staticmethod
    def calculate_weight(result_type):
        """ Different weights for the different versions of the result """
        if result_type == 'Final':
            return 1000
        if 'Official' in result_type:
            return 100 + int(result_type[-1])
        return 1

    def add_result(self, result_type, abs_url, rel_url):
        """ Add a result """
        self.result_url[result_type] = urljoin(abs_url, rel_url)
        weight = Task.calculate_weight(result_type)
        what_to_insert = (
            self.task_number,
            self.task_code,
            self.task_description,
            result_type,
            weight
        )
        cursor = self.database.cursor()
        cursor.execute(INSERT_TASK, what_to_insert)
        self.database.commit()

    def parse_competitors(self):
        """ Parse the competitors """
        parse = CompetitorParser(self.database, list(self.result_url.values())[0])
        parse.save_to_db()

    def save_results_to_db(self):
        """ Bulk to DB """
        for the_key, the_value in self.result_url.items():
            cursor = self.database.cursor()
            query = f'select id from tasks where nb = {self.task_number} and status = \'{the_key}\';'
            cursor.execute(query)
            task_id = cursor.fetchall()[0][0]
            TaskParser(self.database, task_id, the_value)
            print(f'Task {self.task_number}({self.task_code}) version {the_key} Saved')

    def __str__(self):
        """ Convert to string """
        ret_str = f'Task number: {self.task_number} was a {self.task_code} '
        ret_str += f'({self.task_description}) and has the following results:\n'
        for the_key, the_value in self.result_url.items():
            ret_str += f'\t{the_key}: {the_value}\n'
        return ret_str

def clean(word):
    """ Clean a string """
    return ''.join(
        letter for letter in word if
            'a' <= letter <= 'z' or
            '0' <= letter <= '9' or
            letter == ' '
    )

def html_from_url(url_to_get, print_page=False):
    """ HTML code from a URL """
    with urlopen(url_to_get) as the_url_reader:
        if print_page:
            print(the_url_reader.read())
        return html.fromstring(the_url_reader.read())

if __name__ == '__main__':
    THE_URL = 'http://www.sibf.biz/2018Results/Bootstrap/SA18Index.html'

    if exists('mydb.sqlite'):
        remove('mydb.sqlite')
    db = sqlite3.connect('mydb.sqlite')
    db.execute('''pragma synchronous=0''')
    db.execute(CREATE_TASK_TABLE)
    page = html_from_url(THE_URL)
    task_list = []
    for link in page.xpath("//a"):
        if link.text:
            orig_text = link.text
            orig_URL = link.get('href')
            clean_text = re.sub(r'\s+', ' ', orig_text).strip()
            if 'TaskResultsAccordion' in orig_URL:
                reg_exp = re.compile(r'(\d+)\s(.*)\s[(](.*)[)]')
                data = reg_exp.match(clean_text)
                task_list.append(Task(db, data.group(1), data.group(2), data.group(3)))
            elif 'TaskResult' in orig_URL:
                task_list[-1].add_result(orig_text, THE_URL, orig_URL)
    task_list[0].parse_competitors()
    for task in task_list:
        task.save_results_to_db()
    db.execute(CREATE_VIEW_LAST_TASKS)
    db.commit()
