""" Main """

# ---------------------------------------- IMPORT HERE ----------------------------------------

import atexit, itertools, json, nltk, os, pickle, platform, ssl, subprocess, sys, threading, time
import pandas as pd
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from construct_index import Construct_index
from query import Query
from ranking import Ranking

# ---------------------------------------- INIT ----------------------------------------

nltk.download('stopwords')
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')
nltk.download('omw-1.4')

folder_path = os.path.relpath("../TelevisionNews")
index_name = 'indexfile'
progress_done = False
exit_command = "Ctrl + C"

# ---------------------------------------- MAIN FUNCTION ----------------------------------------

if __name__ == '__main__':
    # Cleanup handler
    def cleanup():
        print("\nGot {}! Cleaning up and gracefully exiting...".format(exit_command))

        sys.exit(1)

    atexit.register(cleanup)



    if (os.path.exists(index_name)): # Index has not been constructed yet
        print("\nIndex is now being constructed.")
        index_construct = Construct_index(folder_path)

        index_construct.construct_index()
        indexes_data = index_construct.collect_index() # Indexes ,index_mapping, idf_dict

        # Write the index to a file
        with open(index_name, 'wb') as fp:
            pickle.dump(indexes_data, fp)

        del index_construct

    # Load index
    print("Loading")

    with open(index_name, 'rb') as fp:
        indexes, index_mapping, idf_dict = pickle.load(fp)

    progress_done = True

    # Initialize Query object
    q = Query()

    # Initialize Ranking object
    r = Ranking(1)

    # Initialize JSON Output
    json_out = dict()

    # Query Loop
    while True:
        try:
            print("\nPlease choose your query type: (Do {} anytime to exit):".format(exit_command))
            print("1. Simple Query")
            print("2. Phrase Query")
            print("3. Wildcard Query")
            choice = int(input("Enter choice number: ").strip())

            if choice > 3 or choice <1:
                print("Invalid choice")
                continue

            print("\nPlease choose your ranking type: (Do Ctrl+C anytime to exit):")
            print("1. Cosine Similarity")
            print("2. Summation of tf-idf scores w.r.t document")
            print("3. Summation of (tf-idf w.r.t doc * tf-idf w.r.t query)  ")
            r_choice = int(input("Enter choice number: ").strip())
            print()
            r.choice = r_choice

            if r.choice > 3 or r.choice <1:
                print("Invalid choice")
                continue

            print("\nPlease type your query (Do {} anytime to exit):".format(exit_command))
            q.text = input()

            k = int(input("Enter K (Top K documents will be returned): ")) # to return top k documents

            json_filename = "(" + q.text + ")+choice-" + str(choice) + "__r_choice-" + str(r_choice) + "_" + time.strftime("%Y-%m-%d___%H-%M-%S") + ".json"

            q.parse(index_mapping)

            if choice == 2:
                q.isPhrase = 1

            elif choice == 3: # indicates a wildcard query
                q.isWC = 1

            results = q.search(indexes)


            final_results = r.rank_all(q.text, results, indexes, idf_dict, q.isWC)


            # Write results as json format
            json_out["results"] = len(final_results)
            json_out["hits"] = []

            for docid, score, index in (final_results[:k]):
                # print("DocID: {:5}, Score: {:7.4f}, Index Name: {:15}".format(docid, score, index_mapping[index]))
                filepath = os.path.join(folder_path, index_mapping[index])

                pd_dataframe = pd.read_csv(filepath)
                snippet_column = pd_dataframe["Snippet"]
                #text_column = pd_dataframe["Text"]
                url_column = pd_dataframe["URL"]

                json_out["hits"].append({
                    '_index': index_mapping[index],
                    '_score': score,
                    '_doc_id': docid,
                    '_path': filepath,
                    '_url': url_column[docid],
                    '_snippet': snippet_column[docid],
                    #'_text' : text_column[docid]
                })
                
            # Writing Json to file
            json_filename = json_filename.replace('*','_')

            with open(json_filename, 'w') as json_outfile:
                json.dump(json_out, json_outfile, indent = 4)

            json_out.clear()

            print("\nLook at the file named '{}' in the current directory for the output\n----------".format(json_filename))

        except ValueError:
            print("\nPlease enter valid choice")
            continue
