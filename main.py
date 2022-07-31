"""
Evaluate how well the mapping is working based on the detoxify model's judgement.
"""

import matplotlib
from matplotlib import pyplot as plt
import os
from safeworder import NSFWReplacer, Checker
from tqdm import tqdm
import praw
import json
import pandas as pd
FILES = "files/"
matplotlib.style.use('ggplot')
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

def load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def populate_uncensored(subredditname, limit):


    reddit_creds = load_json("credentials/reddit.json")
    r = praw.Reddit(client_id=reddit_creds["id"],
                    client_secret=reddit_creds["secret"],
                    user_agent=reddit_creds["agent"]
                    )

    top_posts = r.subreddit(subredditname).top(limit=limit, time_filter="all")
    listed = list(top_posts)

    texts = []
    j = 0
    for post in listed:
        texts.append(post.title)
        texts.append(post.selftext)
        comments = post.comments
        for i in range(min((len(comments), 10))):
            comment = comments[i]
            texts.append(comment.body)

        j += 1
        print("downloaded:", j)

    sentences = sum([text.split(".") for text in texts], [])
    no_enter = [t.replace("\n", " ") for t in sentences]
    df = pd.DataFrame.from_dict({"sentences": no_enter})
    df.to_csv(FILES + subredditname + "_uncensored.csv", index=False)

def evaluate(subredditname):

    model = Checker()
    uncensored = pd.read_csv(FILES + subredditname +"_uncensored.csv")
    obscene = []
    obscene_fixed = []
    results = []
    results_censored = []
    rp = NSFWReplacer(checker=model)

    for sentence in tqdm(uncensored.sentences):

        if pd.isnull(sentence):
            continue

        sentence_censored = rp.replace(sentence)[0]
        result = model.calculate_scores(sentence)
        results.append(result)
        result_censored = model.calculate_scores(sentence_censored)
        results_censored.append(result_censored)
        if result_censored["obscene"] >= 0.3:

            #print(sentence_censored)
            #print(result)
            #print(result_censored)
            obscene.append(sentence)
            obscene_fixed.append(sentence_censored)


    uncensored_results_df = pd.DataFrame.from_dict(results)
    censored_results_df = pd.DataFrame.from_dict(results_censored)
    uncensored_results_df.mean().plot(kind="bar", color="orange", rot=10, title= "/r/" +subredditname)
    censored_results_df.mean().plot(kind="bar", color="green", rot = 10, title="/r/" +subredditname)
    plt.legend(["no processing", "sensitive expressions replaced"])
    plt.savefig(FILES + subredditname + "_results.png", dpi=600)
    plt.show()
    print(uncensored_results_df.mean())
    print(censored_results_df.mean())

    df = pd.DataFrame.from_dict({"obscene":obscene, "to_be_corrected":obscene, "censored":obscene_fixed})
    df.to_csv(FILES + subredditname + "_fix_this.csv")


limit = 100

subredditname = "askreddit"
#populate_uncensored(subredditname, limit)
evaluate(subredditname)


subredditname = "sexstories"
#populate_uncensored(subredditname, limit)
evaluate(subredditname)
