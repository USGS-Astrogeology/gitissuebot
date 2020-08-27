from datetime import timedelta, datetime
from unittest import mock
import pytest
import requests_mock
import requests

from gitissuebot.main import get_issues, update_with_message, add_label, close_issue, find_most_recent_activity, run_query, update_inactive_issues

# test that a response comes back with a 200 and a .json() method

def test_exception_run_query(requests_mock):
    requests_mock.post('mock://test.org', status_code=400)
    with pytest.raises(Exception):
        run_query('foo')

def test_run_successful_query(requests_mock):
    requests_mock.post('mock://test.org', status_code=200, json={'foo':'bar'})
    resp = run_query('some_query')
    assert resp == {'foo':'bar'}

def test_get_issues():
    response_str = {'data':{'repository':{'openIssues':{'edges':[{'node':'a', 'cursor': 'some_cursor'},
                                                                 {'node':'b', 'cursor': 'some_cursor'},
                                                                 {'node':'c', 'cursor': 'some_cursor'}]}}}}
    response = lambda x: response_str
    issues, cursor = get_issues(query_func=response)
    assert issues == ['a', 'b', 'c']
    assert cursor == 'some_cursor'

# Case where comment is newest
# Case where reaction is newest
# Case where comment is newest assuming author is the bot of a newer
# Case where reaction is newest assuming author is the bot of the newer
@pytest.mark.parametrize('times, names, position_of_newest, expected', [
    ([ f'{i}-1-1T00:00:00Z' for i in range(2000,2010)], ['a', 'b', 'c'], 3, datetime(2010,1,1)), # Newest reaction
    ([ f'{i}-1-1T00:00:00Z' for i in range(2000,2010)], ['a', 'b', 'c'], 9, datetime(2010,1,1)), # Newest comment
    ([ f'{i}-1-1T00:00:00Z' for i in range(2000,2010)], ['a', 'b', 'ascbot'], 8, datetime(2007,1,1)), # Newesst is the bot/ignored, newest is then the preceeding comment
    ([ f'{i}-1-1T00:00:00Z' for i in range(2000,2010)], ['a', 'b', 'ascbot'], 4, datetime(2010,1,1))
    ])
def test_find_most_recent_activity(times, names, position_of_newest, expected):
    # Modify the times list to make the position of newest the newest.
    times[position_of_newest] = '2010-1-1T00:00:00Z'
    with mock.patch('gitissuebot.main.datetime') as dtmock:
        dtmock.utcnow.return_value = expected
        # This way the utcnow is mocked, but the strptime call passes through unmocked.
        dtmock.strptime.side_effect = lambda *args, **kwargs: datetime.strptime(*args, **kwargs)
        issue = {'createdAt':times[0],
                'comments':{'edges':[
                    {'node':{'createdAt':times[1],
                            'updatedAt':times[2],
                            'author':{'login':names[0]},
                            'reactions':{'edges':[
                                {'node':{'createdAt':times[3]}},
                                {'node':{'createdAt':times[4]}}
                            ]}}},
                    {'node':{'createdAt':times[5],
                            'updatedAt':times[6],
                            'author':{'login':names[1]},
                            'reactions':{'edges':[
                                {'node':{'createdAt':times[7]}}
                                ]}}},
                    {'node':{'createdAt':times[8],
                            'updatedAt':times[9],
                            'author':{'login':names[2]},
                            'reactions':{'edges':[
                                ]}}},
                ]}}
        age = find_most_recent_activity(issue)
        print(age)
    assert age.days == 0


def test_update_with_message():

    issueid = 0
    message = 'test'
    query_func = lambda x: x
    resp = update_with_message(issueid, message, query_func=query_func)
    assert 'addComment' in resp
    assert 'subjectId: "0"' in resp
    assert 'body:"test"' in resp
    assert 'mutation' in resp

def test_add_label():
    issueid = 0
    labelid = 'mystery'
    query_func = lambda x: x
    resp = add_label(issueid, labelid, query_func=query_func)
    assert 'addLabelsToLabelable' in resp
    assert 'labelableId:"0"' in resp
    assert 'labelIds:["mystery"]' in resp

def test_close_issue():
    issueid = 0
    query_func = lambda x: x
    resp = close_issue(issueid, query_func=query_func)
    assert 'mutation' in resp
    assert 'closeIssue' in resp
    assert 'issueId:"0"' in resp

def test_inactive_182():
    with mock.patch('gitissuebot.main.find_most_recent_activity', return_value=timedelta(182)) as fmr,\
        mock.patch('gitissuebot.main.update_with_message') as update,\
        mock.patch('gitissuebot.main.add_label') as label:
        update_inactive_issues([{'id':"foo"},])
        assert fmr.called
        assert update.called
        assert label.called

def test_inactive_335():
    with mock.patch('gitissuebot.main.find_most_recent_activity', return_value=timedelta(335)) as fmr,\
        mock.patch('gitissuebot.main.update_with_message') as update:
        update_inactive_issues([{'id':"foo"},])
        assert fmr.called
        assert update.called

    with mock.patch('gitissuebot.main.find_most_recent_activity', return_value=timedelta(366)) as fmr,\
        mock.patch('gitissuebot.main.update_with_message') as update,\
        mock.patch('gitissuebot.main.add_label') as label,\
        mock.patch('gitissuebot.main.close_issue') as close:
        update_inactive_issues([{'id':"foo"},])
        assert fmr.called
        assert update.called
        assert label.called
        assert close.called
