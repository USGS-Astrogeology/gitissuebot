from datetime import datetime
import requests

from .settings import config

def run_query(query):
    """
    Runs a GraphQL query against the GitHub API.

    Parameters
    ----------
    query : str
            The GraphQL string query to be passed to the API

    Returns
    -------
      : dict
        The JSON (dict) response from the API
    """
    headers = {"Authorization": f"Bearer {config['APIKEY']}"}
    request = requests.post(config['git_url'], json={'query':query}, headers=headers, verify=config['ssl_cert'])
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))

def get_issues(query_func=run_query, issue_filter="states: OPEN, first:1"):
    """
    Get all of the open issues in a repository.

    Returns
    -------
      : dict
        GitHub API response parsed to the individual issues (through
        edges and nodes in the response).
    """
    # Query to get issues, comments, and reactions to comments; the `last:1` is currently hard coded to only impact a single issue. Remove to process all.
    query = f"""
    query {{
      repository(owner:"{config['owner']}", name:"{config['repository']}") {{
        openIssues: issues({issue_filter}) {{
          edges {{
            node {{
              id
              title
              updatedAt
              createdAt
              url
              labels(first:100) {{
                  edges {{
                    node {{
                      id
                      name
                    }}
                  }}
                }}
              comments(last:100) {{
                edges {{
                  node {{
                    author {{login}}
                    updatedAt
                    createdAt
                    reactions(last:1) {{
                      edges {{
                        node {{
                          createdAt
                        }}
                      }}
                    }}
                  }}
                }}
              }}
            }} cursor
          }}
          pageInfo {{
            startCursor
            endCursor
          }}
        }}
      }}
    }}
    """
    response = query_func(query) # Execute the query
    if 'data' not in response.keys():
        print(response)
    elif 'errors' in response.keys():
        print(response['errors'])
    result = response['data']['repository']['openIssues']['edges']
    return [issue['node'] for issue in result], result[-1]['cursor']

def find_most_recent_activity(issue):
    """
    This func finds the most recent activity on an issue by iterating over all of
    the content, omitting any posts by the bot, and finding the most recent UTC
    timestamp.

    Parameters
    ----------
    issue : dict
            The JSON (dict) response from the github API for a single issue. We
            assume that the 'node' key has been omitted.

    Returns
    -------
    age : obj
          A datetime.timedelta object
    """
    dates = []
    # Intentionally skip the last updated at key because this could be the bot talking.
    dates.append(issue['createdAt'])

    # Step over all the comments; ignore the bot and reactions to the bot.
    for comment in issue['comments']['edges']:
        comment = comment['node']

        if comment['author']['login'] == 'ascbot':
            continue
        dates.append(comment['updatedAt'])
        dates.append(comment['createdAt'])

        # Step over any reactions
        for reaction in comment['reactions']['edges']:
            reaction = reaction['node']
            dates.append(reaction['createdAt'])
    newest_activity = max(dates)
    age = datetime.utcnow() - datetime.strptime(newest_activity, '%Y-%m-%dT%H:%M:%SZ')
    return age

def update_with_message(issueid, msg, query_func=run_query):
    """
    Using the Github V4 GraphQL API, update an issue
    with a given message.

    Parameters
    ----------
    issueid : str
              The GitHub hashed issue identifier

    msg : str
          The string message to be posted by the API key holder

    Returns
    -------
      : dict
        The JSON (dict) response from the GitHub API
    """
    # Add a comment query
    query = f"""
    mutation {{
      addComment(input:{{
        subjectId: "{issueid}",
        body:"{msg}"
      }}) {{
        clientMutationId
      }}
    }}
    """
    return query_func(query)

def add_label(issueid, labelid, query_func=run_query):
    """
    Using the Github V4 GraphQL API, add a
    label to an issue.

    Parameters
    ----------
    issueid : str
              The GitHub hashed issue identifier

    labelid : str
              The GitHub hashed label identifier

    Returns
    -------
      : dict
        The JSON (dict) response from the GitHub API
    """
    query = f"""mutation {{
      addLabelsToLabelable(input:{{
        labelableId:"{issueid}",
        labelIds:["{labelid}"]
      }}) {{
        clientMutationId
      }}
    }}"""
    return query_func(query)


def remove_label(issueid, labelid, query_func=run_query):
    """
    Using the Github V4 GraphQL API, add a
    label to an issue.

    Parameters
    ----------
    issueid : str
              The GitHub hashed issue identifier

    labelid : str
              The GitHub hashed label identifier

    Returns
    -------
      : dict
        The JSON (dict) response from the GitHub API
    """
    query = f"""mutation {{
      removeLabelsFromLabelable(input:{{
        labelableId:"{issueid}",
        labelIds:["{labelid}"]
      }}) {{
        clientMutationId
      }}
    }}"""
    return query_func(query)

def close_issue(issueid, query_func=run_query):
    """
    Using the Github V4 GraphQL API, close
    an issue.

    Parameters
    ----------
    issueid : str
              The GitHub hashed issue identifier

    Returns
    -------
      : dict
        The JSON (dict) response from the GitHub API
    """
    query = f"""mutation {{
      closeIssue(input:{{
        issueId:"{issueid}"
      }}) {{
        clientMutationId
      }}
    }}"""
    return query_func(query)

def update_inactive_issues(issues, query_func=run_query):
    """
    Parse a list of of GitHub API response issues and
    update those issue which meet the inactivity criteria.

    Issues with no activity in the last 182 are updated with
    the `inactive` label and a message.

    Issues with no activity in 335 days are updated with a
    nudge message.

    Issues with no activity after 365 days are closed with
    a message and an `automatically_closed` label.

    Parameters
    ----------
    issues : list
             of JSON (dict) issues from the GitHub API parsed
             down to the individual nodes (issues)
    """
    labelids = config['labelids']

    for issue in issues:
        age = find_most_recent_activity(issue)
        try:
            issue_labels = [x['node']['name'] for x in issue['labels']['edges']]
        except KeyError:
            issue_labels = []
        if age.days >= 365:
            resp = update_with_message(issue['id'], config['final_message'], query_func=query_func)
            resp = add_label(issue['id'], labelids['automatically_closed'], query_func=query_func)
            resp = close_issue(issue['id'], query_func=query_func)
        elif age.days >= 335 and 'pending_closure' not in issue_labels:
            resp = update_with_message(issue['id'], config['second_message'], query_func=query_func)
            resp = add_label(issue['id'], labelids['pending_closure'], query_func=query_func)
        elif age.days >= 182 and age.days <= 334 and 'inactive' not in issue_labels:
            resp = update_with_message(issue['id'], config['first_message'], query_func=query_func)
            resp = add_label(issue['id'], labelids['inactive'], query_func=query_func)


def remove_inactive_label(issues, query_func=run_query):
    """
    Remove "inactive" and "pending_closure" labels from issues
    when new activity takes place.


    Parameters
    ----------
    issues : list
             of JSON (dict) issues with inactive / pending_closure label
             from the GitHub API parsed down to the individual nodes (issues)
    """
    labelids = config['labelids']

    for issue in issues:
        age = find_most_recent_activity(issue)
        if age.days < 182:
            resp = remove_label(issue['id'],
                                [labelids['pending_closure'], labelids['inactive']],
                                query_func=query_func)
