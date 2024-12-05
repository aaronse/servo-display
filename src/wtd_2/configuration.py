import json
import os



# USAGE:
#   confjson = Configuration.load('conf.json')
# Based on:
#   https://stackoverflow.com/questions/19078170/python-how-would-you-save-a-simple-settings-config-file

class Dict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Configuration(object):

    DEFAULT_CONFIG_PATH = "defaultConfig.json"
    CONFIG_PATH = "config.json"

    @staticmethod
    def __load__(data):
        if type(data) is dict:
            return Configuration.load_dict(data)
        else:
            return data


    @staticmethod
    def load_dict(data: dict):
        result = Dict()
        for key, value in data.items():
            result[key] = Configuration.__load__(value)
        return result


    @staticmethod
    def load(path: str):
        with open(path, "r") as f:
            result = Configuration.__load__(json.loads(f.read()))
        return result


    @staticmethod
    def removeComments(data):
        result = ""
        for line in data.split("\n"):
            if line.strip().startswith("//") or line.strip().startswith("#"):
                continue

            result += line + "\n"

        return result


    @staticmethod
    def load(configPath: str = CONFIG_PATH, defaultConfigPath: str = DEFAULT_CONFIG_PATH):
        if (os.path.exists(configPath)):
            with open(configPath, "r") as f:
                dataStr = Configuration.removeComments(f.read())
                result = Configuration.__load__(json.loads(dataStr))
                print("Config loaded, path=" + configPath)
                return result

        with open(defaultConfigPath, "r") as f:
            dataStr = Configuration.removeComments(f.read())
            print(dataStr)
            result = Configuration.__load__(json.loads(dataStr))
            print("Config loaded, path=" + defaultConfigPath)
            return result


    @staticmethod
    def save(config):
        path = Configuration.CONFIG_PATH

        with open(path, "w")  as f:
            json.dump(config, f, indent = 4)

