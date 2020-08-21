import os
import yaml

def configure():
  # Load the config and get the headers setup
  config = os.environ.get('GITISSUEBOT_CONFIG', None)
  if not config:
    return
  with open('config.yml', 'r') as stream:
      config = yaml.load(stream)
  return config

  config = configure()