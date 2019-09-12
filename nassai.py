import csv
import os
from datetime import datetime

import click

from code.custom import LSTMClassifier, BLSTM2DCNN, FCholletCNN, YKimCNN
from code.mlp import mlp_model
from code.sklearn_classifiers import BernNB, SVM, LinearSVM, MLP
from code.train import train
from code.utils import get_path, load_model
from code.build import BuildEmbeddingModel


@click.command()
@click.argument('action', type=click.Choice(['preprocess', 'build_embedding', 'train', 'predict']))
@click.option('--dbow', type=click.INT, default=1, help='Uses DBOW if true. DM if false.')
@click.option('--use_glove', type=click.INT, default=1, help='Train classifier with glove embedding or prebuilt embedding from this data.')
@click.option('--cbow', type=click.INT, default=1, help='Uses DBOW if true. DM if false.')
@click.option('--batch', type=click.INT, default=200, help='Batch for training keras model')
@click.option('--epoch', type=click.INT, default=200, help='Epoch for training keras model')
@click.option('--using', type=click.Choice(['sklearn', 'keras']), help='Algorithm to train data on.')
@click.option('--mode', type=click.Choice(['tfidf', 'doc2vec', 'word2vec']), help='Algorithm to train data on.')
@click.option('--text', type=click.STRING, help="String to predict for")
def nassai_cli(action, cbow, batch, epoch, using, dbow, mode, text, use_glove=1):
    base_data_path = get_path('data') + "/final_with_dates.csv"
    clean_data_path = get_path('data') + "/clean_data.csv"

    if action == "preprocess":
        from code import preprocessing
        return preprocessing.preprocess_data(base_data_path)
    elif action == "build_embedding":
        if mode == "doc2vec":
            builder = BuildEmbeddingModel(embedding_type="doc2vec", data=clean_data_path, doc2vec_mode=dbow, epoch=epoch, batch=batch)
            return builder.build_model()
        builder = BuildEmbeddingModel(embedding_type="word2vec", data=clean_data_path, word2vec_mode=cbow, epoch=epoch, batch=batch)
        return builder.build_model()
    elif action == "train":
        if mode == "doc2vec":
            embedding = get_path('models') + '/doc2vec/nassai_dbow_doc2vec.vec'
            if using == "sklearn":
                model_list = [
                              ("doc2vec_bnb_mean_embedding", BernNB(use_glove=False, embedding_path=embedding, use_tfidf=False, tfidf="mean_embedding")),
                              ("doc2vec_svm_mean_embedding", SVM(use_glove=False, use_tfidf=False, embedding_path=embedding, tfidf="mean_embedding")),
                              ("doc2vec_linear_svm_mean_embedding", LinearSVM(use_glove=False, use_tfidf=False, embedding_path=embedding, tfidf="mean_embedding")),

                              ("doc2vec_bnb_tfidfemmbedding", BernNB(use_glove=True, use_tfidf=True, tfidf="tfidf_embedding_vectorizer")),
                              ("doc2vec_svm_tfidfembedding", (SVM(use_glove=True, use_tfidf=True, tfidf="tfidf_embedding_vectorizer"))),
                              ("doc2vec_linear_svm_tfidfembedding", LinearSVM(use_glove=True, use_tfidf=True, tfidf="tfidf_embedding_vectorizer"))

                              ]
            else:
                model_list = [
                                ("lstm_doc2vec_glove", LSTMClassifier(train_embeddings=False, batch=True, use_glove=True, units=256, embedding_path=embedding, layers=4)),
                                ("fchollet_cnn_doc2vec_glove", FCholletCNN(train_embeddings=False, batch=True, use_glove=True, units=256, embedding_path=embedding)),
                                ("bilstm_doc2vec_glove", BLSTM2DCNN(train_embeddings=False, batch=True, use_glove=True, units=256, embedding_path=embedding)),
                                ("ykimcnn_doc2vec_glove", YKimCNN(train_embeddings=False, batch=True, use_glove=True, units=256, embedding_path=embedding))
                              ]
        elif mode == "word2vec":
            if using == "sklearn":
                model_list = [
                              ("bnb_mean_embedding", BernNB(use_glove=True, use_tfidf=False, tfidf="mean_embedding")),
                              ("svm_mean_embedding", (SVM(use_glove=True, use_tfidf=False, tfidf="mean_embedding"))),
                              ("linear_svm_mean_embedding", LinearSVM(use_glove=True, use_tfidf=False, tfidf="mean_embedding")),

                              ("bnb_tfidfemmbedding", BernNB(use_glove=True, use_tfidf=True, tfidf="tfidf_embedding_vectorizer")),
                              ("svm_tfidfembedding", (SVM(use_glove=True, use_tfidf=True, tfidf="tfidf_embedding_vectorizer"))),
                              ("linear_svm_tfidfembedding", LinearSVM(use_glove=True, use_tfidf=True, tfidf="tfidf_embedding_vectorizer"))]
            else:
                model_list = [("mlp_mean_embedding", MLP(use_glove=True, use_tfidf=False, tfidf="mean_embedding"), 1),
                              ("mlp_tfidfemmbedding", MLP(use_glove=True, use_tfidf=False, tfidf="tfidf_embedding_vectorizer"), 1)]
        else:
            if using != "sklearn":
                model_list = [("bilstm-cnn", FCholletCNN(train_embeddings=True, batch=True, use_glove=False, units=256)),
                              ("LSTMClassifier", LSTMClassifier(train_embeddings=True, batch=True, use_glove=False, units=256, layers=4))]
            else:
                model_list = [("tfidf_mlp", BernNB(use_glove=False, use_tfidf=True)),
                              ("tfidf_linear_svm_mean_embedding", LinearSVM(use_glove=False, use_tfidf=True, tfidf="mean_embedding")),
                              ("tfidf_svm", (SVM(use_glove=False, use_tfidf=True))), ("linear_svm", LinearSVM(use_glove=False, use_tfidf=True))]

        return run(model_list, mode=mode, using=using, layers=4, dropout_rate=0.25)

    else:
        model = load_model(mode, using)
        pred = model.predict([text])
        click.echo("TEXT : {}".format(text))
        print()
        click.echo("PREDICTION: {}".format(pred))


def run(model_list, mode, **kwargs):
    records = {}
    results_path = get_path('data') + '/results.csv'
    clean_data_path = get_path('data') + '/clean_data.csv'
    print("TRAINING : {}".format(mode))
    for model in model_list:
        print("Current Model : {}".format(model))
        score, duration = train(clf=model, data=clean_data_path, name="{}_{}".format(model[0], mode), **kwargs)
        records.update({
            'date': datetime.now(),
            'f1': score,
            'mode': mode,
            'duration': duration,
            'model_name': model[0],
            'using': kwargs.get('using')
        })
        print("{0} took {1}".format(model, duration))
        with open(results_path, 'a') as f:
            w = csv.DictWriter(f, records.keys())
            w.writerow(records)


if __name__ == "__main__":
    nassai_cli()
