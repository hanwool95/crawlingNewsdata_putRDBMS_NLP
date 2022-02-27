import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from tqdm import tqdm
import re
from config import apiurl


rawdata = pd.read_csv('NewsResult.csv')


def replace_string_stopword(string):
    stop_word_list = ["'", '"', '.', ',', '‘', '’', '…', '·', " ", '…', '↓', '…']
    result = string
    for stword in stop_word_list:
        result = result.replace(stword, "")
    return result


def get_pageurls_from_df(result_df):
    page_former_naver = "https://search.naver.com/search.naver?where=news&sm=tab_jum&query="
    page_urls_naver = []
    for title in result_df['수정제목']:
        page_url_naver = page_former_naver + title
        page_urls_naver.append(page_url_naver)

    return page_urls_naver


def crawling_information_from_areas_title(areas, comparing_origin_title, i):
    indice = []
    titles = []
    naver_urls = []
    for area in areas:
        title = area.select("a.news_tit")[0]["title"]

        comparing_title = replace_string_stopword(title)
        if comparing_origin_title == comparing_title:
            indice.append(i)
            titles.append(title)

            if "네이버뉴스" in area.select("div.info_group")[0].get_text():
                n_url = area.select("div.info_group > a.info")[1]["href"]
                naver_urls.append(n_url)
                break
            else:
                naver_urls.append("네이버뉴스없음")
    return indice, titles, naver_urls


def crawling_sub_areas(sub_areas, comparing_origin_title, i):
    indice = []
    titles = []
    naver_urls = []
    for area in sub_areas:
        sub_title = area.select("a.elss.sub_tit")[0]["title"]
        comparing_title = replace_string_stopword(sub_title)
        if (comparing_origin_title == comparing_title) and area.select("a.sub_txt"):
            indice.append(i)
            titles.append(sub_title)
            if "네이버뉴스" in area.select("a.sub_txt")[0].get_text():
                print("find sub naver news")
                print(sub_title)
                n_url = area.select("a.sub_txt")[0]["href"]
                naver_urls.append(n_url)
                break
            else:
                naver_urls.append("네이버뉴스없음")
    return indice, titles, naver_urls


def match_case_naver(areas, i, origin_title, sub_areas):
    comparing_origin_title = replace_string_stopword(origin_title)
    indice, titles, naver_urls = crawling_information_from_areas_title(areas, comparing_origin_title, i)

    df = pd.DataFrame({
        "index": indice,
        "title": titles,
        "naver_url": naver_urls}
    )

    if df.shape[0] == 0:
        if len(sub_areas) > 0:
            indice, titles, naver_urls = crawling_sub_areas(sub_areas, comparing_origin_title, i)
            df = pd.DataFrame({
                "index": indice,
                "title": titles,
                "naver_url": naver_urls}
            )
        else:
            data = pd.DataFrame({
                "index": [i],
                "title": ["매칭결과없음"],
                "naver_url": ["매칭결과없음"]
            })
            df = pd.concat([df, data])
            return naver_urls, df

    naver_news = df.naver_url.isin(["네이버뉴스없음"])
    if df[~naver_news].shape[0] > 0:
        return naver_urls, df[~naver_news]
    else:
        return naver_urls, df[naver_news].iloc[:1, :]


def flatten(l):
    flatList = []
    for elem in l:
        if type(elem) == list:
            for e in elem:
                flatList.append(e)
        else:
            flatList.append(elem)
    return flatList


def make_comment_list(n_url):

    if len(n_url) > 0 and (n_url[0] != '네이버뉴스없음'):
        print("getting comment from ", n_url)
        url = n_url[0]
        comment_list = []
        page = 1
        while True:
            oid = url.split("oid=")[1].split("&")[0]
            aid = url.split("aid=")[1]

            c_url = apiurl + oid + "%2C" + aid + \
                    "&categoryId=&pageSize=20&indexSize=10&groupId=&listType=OBJECT&pageType=more&page=" + str(page) + \
                    "&refresh=false&sort=FAVORITE"

            header = {
                "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
                "referer": url,
            }

            r = requests.get(c_url, headers=header)
            cont = BeautifulSoup(r.content, "html.parser")
            total_comm = str(cont).split('comment":')[1].split(",")[0]

            match = re.findall('"contents":([^\*]*),"userIdNo"', str(cont))
            comment_list.append(match)
            if int(total_comm) <= ((page) * 20):
                break
            else:
                page += 1

        allComments = flatten(comment_list)
    else:
        allComments = []
    return allComments


def csv_out(result_df, result_naver, comment_naver):
    test_df = result_df.reset_index()
    total_naver = pd.merge(test_df, result_naver, how='left', left_on='index', right_on='index')
    total_naver.to_csv('new_total.csv', encoding='utf-8-sig', index=False)
    comment_naver.to_csv('new_total_comment.csv', encoding='utf-8-sig', index=False)


def total_crawling_process(result_df, page_urls_naver, origin_titles):
    result_naver = pd.DataFrame()
    comment_naver = pd.DataFrame()

    for i, origin_title, page_url_naver in tqdm(zip(result_df.index, origin_titles, page_urls_naver)):

        r = requests.get(page_url_naver)
        soup = BeautifulSoup(r.text, "html.parser")
        time.sleep(0.5)

        areas = soup.select('div.news_area')
        if len(areas) == 0:
            data = pd.DataFrame({
                "index": [i],
                "title": ["검색결과없음"],
                "naver_url": ["검색결과없음"]
            })
            result_naver = pd.concat([result_naver, data])
        else:
            sub_areas = soup.select('ul.list_cluster')
            n_urls, case = match_case_naver(areas, i, origin_title, sub_areas)
            result_naver = pd.concat([result_naver, case])

            comment_list = make_comment_list(n_urls)
            for comment in comment_list:
                revised_comment = comment[1:-1]
                data = pd.DataFrame({
                    "index": [i],
                    "comment": [revised_comment]
                })
                comment_naver = pd.concat([comment_naver, data])
    return result_df, result_naver, comment_naver

def main():
    rawdata['수정제목'] = rawdata.iloc[:, 2].str.replace('\'|"|`|“|‘|”|’', '', regex=True)

    page_urls_naver = get_pageurls_from_df(rawdata)

    origin_titles = rawdata['제목']

    result_df, result_naver, comment_naver = total_crawling_process(rawdata, page_urls_naver, origin_titles)

    csv_out(result_df, result_naver, comment_naver)





if __name__ == "__main__":
    main()


