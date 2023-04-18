---
layout: post
title:  "QA for search results"
author: Simon Schneider
date:   2023-05-01 22:59:00 +0100
categories: search elasticsearch solr
header_image: /img/posts/2023-05-01-qa-for-search-results-header.png
# Social Media
image: /img/posts/2023-05-01-qa-for-search-results-card.png
description: Quality assurance for search results
twitter:
  username: raynigon
---
# Introduction
<p style="font-weight: bold;text-align: center;">
"As a user I want to find the item I want to interact with."
</p>
This user story is one of the most complicated ones to implement.
The average user does not care how a search engine generates the results they receive, 
when they type some characters into the search input field.
The average user only cares, whether the returned results are relevant or not.
The described user story often needs teams of highly trained software engineers to be implemented correctly.
Therefore the following question arises: "Why does it take so much effort to implement a good search service?"
There are many reasons why information retrieval is difficult. 
First of all, search results are ambiguous.
For instance, there are two users searching for the term "red bar". 
The first user wants to find the local pub with a red sign above the door, 
whereas the second user looks for a chocolate bar with a red package.
A search service has to deal with these inputs and should provide the best matching result for each user,
even in such complicated and context dependent cases as described above.
If a context is given, e.g. online grocery shop, or a library of chemical elements, it is easier to create less ambiguous result sets.
But even then, there is no practical way to ensure a user gets only the expected results.
Secondly many different requirements of different stakeholder for search results add even more complexity to the task.
Usually, an enterprise with an e-commerce store has the demand to list the products with the highest margin at the top of the result list.
Since users are more likely to buy products which are at the top of the result list [^1]
more sales on high margin products are generated, which increases the overall profit.
Therefore not only the accuracy of the search result itself but also the margin of the product influence the result. 
Thirdly operators of e-commerce stores could do product placement, 
sell slots (specific places in the result list for a certain product when defined search terms are used) 
or recommend products to promote them. If the user searches for one of the defined terms, 
the list will show the corresponding product.
However, this contradicts the users' desire to see the most relevant product displayed at the top of the search results.
These conflicting requirements have to be managed for each search service.
And finally as described above, much effort is needed to create a good search service.
To ensure the investment has a durable effect on the software system, 
the following question is extremely relevant:
<p style="font-weight: bold;text-align: center;">
    "How to assure, that a search service produces good results?"
</p>
The objective of this blog post is to explain methods which can help to answer this question.
Since all methods are built on top of a search engine, 
the second chapter explains the internal details of lucene based search engines.
The third chapter contains explanations for the most common methods used in quality assurance for search results.
The conclusion provides an approach, how the methods can be used to answer the question above.

# Analysis of Search Engines

In the academic field of information retrieval experts have been addressing the question 
of how to satisfy a user's information need for decades.
A search engine, as an implementation of an information retrieval system, can therefore be modeled as an application, 
which delivers the best matching content for a user's information need.
This application has to have some kind of input to satisfy the users information need.
Often the user has the possibility to submit a search query as an input.
For lucene based search engines, 
a single search result returned by a search engine is called document.
These documents can be text based, but may correspond to content such as:[^2]

* Products
* Songs (e.g. MP3)
* People in a list of contacts
* Word documents
* Pages of a book
* Entire books


Each document contains fields. 
Each field consists of a key and a value[^2].
The key is the name of the field and the value contains the content for this field in the given document.
The functionality of a search engine can now determine the best matching documents
based on the given input and the field values of all documents.
This functionality will be explained in more detail in the following sections.

![Search service and search engine grouping](/img/posts/2023-05-01-search-service-grouping.png)

A search engine is usually domain independent.
This means that a search engine can be used to search through books 
in the same way as to search through chemical structures.
Since these contexts allow to provide completely different query structure and query refining methods,
an additional application is usually exposing the query interface to the user.
This application is called "Query Service".

Often the documents in the search engine have to be added, updated and deleted automatically.
Therefore, another application handles this update process by using external data sources to determine
which documents have to be present in the search engine. 
This application can also refine the documents before ingesting them into the search engine.
This application is called "Ingestion Service".
The whole search service starts with the flow of data in the "Ingestion Service" where the data is consolidated into documents and ingested into the search engine.
The search engine subsequently provides the data to the "Query Service", which enhances the users queries by using context specific information.
This data flow is also shown in in the figure above by the gray arrows.
The following chapters will be ordered by this flow of data.
The section "Indexing" shows how the data provided by the "Ingestion Service" is handled in the search engine.
In section "Querying" the capabilities of a search engine for a query from the "Query Service" are described.

## Indexing
The first key responsibility of a search engine is to ingest and store documents efficiently so that these documents can be retrieved quickly[^3].

### Inverted index
The data structure that forms the core of a search engine is called an inverted index.
This index references the stored documents by the search term.
There are two main components in the inverted index.
The first one is called search term dictionary, 
which is a sorted list of all terms that occur in a specific field across all documents.
Each term has a list of document references attached.
Each document referenced for this term contains the specific term.

![Simple inverted index](/img/posts/2023-05-01-inverted-index.png)

The following statements are true for the documents shown in the figure above:

* "Document 1" contains the terms "blue" and "butterfly"
* "Document 2" contains the terms "best" and "blue"

The inverted index shown in the figure above contains exactly one entry for each term occurring in the documents.
Every entry references all documents in which a term occurs.
The references in the inverted index in the figure above can be described as follows:

* The entry for the term "best" references "Document 2"
* The entry for the term "blue" references "Document 1" and "Document 2"
* The entry for the term "butterfly" references "Document 1".

When the search query for "blue butterfly" is resolved by using this inverted index,
the search engine splits the query into two parts,
queries the inverted index for both terms "blue" and "butterfly" and will then intersect both result sets.
Because the set of documents containing the term "blue" is "1,2" and the set of documents containing the term "butterfly" is "1",
the intersection of document these identifiers is "1" and the search engine will only return the document "Document 1".
In natural language, this means that only "Document 1" contains the two words "Blue" and "Butterfly".

A real implementation of an inverted index consists of more components.
For lucene based search engines, 
the inverted index contains at least the following components[^4]:

* **Doc frequency**, number of documents which contain a particular term
* **Term frequency**, number of times a particular term occurs in a document
* **Term positions**, position of the term in a document
* **Term offsets**, start and end offset of a particular term in a document
* **Payloads**, arbitrary data
* **Stored fields**, original field values
* **Doc values**, auxiliary relevance-scoring heuristic

These data structures will be referred to again in the following chapters,
because they are the main elements of a search engine. 

### Extract, Transform, Load (ETL)

In the ETL process[^5], data from multiple data sources are merged into one target database.
When data are ingested into a search engine, a process similar to the ETL process is used.
The multiple sources can vary, but the target database is the search engine.
Usually, some functionality of this process is done outside of the search engine (e.g. in the "Ingestion Service", see <!--TODO autoref{fig:seanalysis:service:grouping}) -->
and some functionality is implemented in the search engine itself.
The distinction of where functionality is implemented can not be defined in general, 
as it strongly depends on the implementation.

#### Extract
To ingest data into a search engine an extraction process has to be implemented.
For Internet search engines, this process could be a web crawler, which calls different websites and follows the links on this pages.
For each website the crawler creates a document consisting of fields which will be filled with data from the website (e.g. title, language, author, domain, etc.).

#### Transform
The next step in the ingestion process is the analysis of the documents and the transformation into better searchable values.
The first part of this step could be to enhance the documents with additional metadata (e.g. categories like weather, news, movie, music).
Then, the second step would be to analyse the content and improve the query quality, 
e.g. add synonyms, hyphenation (this is important for languages like German where many words are composed),
filter words like "and", "or", "this" and "that" because they add no value to the search result.
When these two parts of the transformation step are done, the document should consist of more and higher quality terms than before.

#### Load
After the document was transformed it can be loaded.
The search engine will store the document and add all terms to the inverted index.
After this step is finished the new document can be retrieved.

## Querying

The second key responsibility of a search engine is to provide a retrieval functionality so that a search can be performed by a user[^3].
In the previous example in the section [Inverted Index](#inverted-index), all given terms had to match for a document to be in the search results.
Also there was no difference between the fields in the documents.
In practice, however, some users want more complex queries to be handled correctly, or want to differentiate between fields.
Search engines provide many mechanisms to handle these complex queries.
The most common ones are Boolean searches, filters and aggregations.

### Boolean search
In the easiest case we do not need Boolean search because only one term is present 
and the search engine will find all documents containing this specific term.
In the example in section [Inverted index](#inverted-index) the "AND" combination was already used to search for multiple terms.
An example for an "AND" combination is the query "blue shoes".
In this case the search engines retrieves all document references which match the first term "blue",
then it retrieves all document references which match the second term "shoes".
The intersection of both result sets is then used to create the final result of documents which are returned to the user.

<p style="font-weight: bold;text-align: center;">
As a user I want to find all blue shoes which I can wear to a dress when searching for "dress shoes blue".
</p>

The user story above could be requirement for a search service.
If the "AND" combination is used for this query it might happen that no document is returned,
because the intersection of all three result sets would be empty.
To solve this problem the query can be improved by adding additional requirements to the terms.

* The matching document must contain the term **blue**
* The matching document should contain the term **dress**
* The matching document must contain the term **shoes**

This could also be written as  "(shoes AND dress AND blue) OR (shoes AND blue)".
In this case, all documents containing the terms "shoes" and "blue" will match the query.
When executing this query, the search engine will retrieve the result sets for all of the three terms,
intersect the result sets of the terms "shoes" and "blue" and placing all documents at the top of the final result set,
which contain the term "dress". The sorting with "OR" queries will be important for "Ranking"[^6].
Besides "AND" and "OR" queries, there are also "NOT" queries.
Lucene based search engines handle Boolean queries a little bit different to the "AND", "OR" and "NOT" syntax.
For a lucene query the terms can be sorted into following clauses[^7]:

* **must**: the term must have a match inside the document.
* **should**: the term might or might not have a match inside the document.
* **must not**: the term must not have a match inside the document and will not be considered a match, even if it does match a "must" clause.
* **should not**: the term might or might not have a match inside the document.

The should queries will be important for Ranking, since they influence where a document is positioned in the result set.

### Filter and aggregations

When searching in huge collections of documents, it is often useful to filter the documents which should be queried.
In Relevant Search[^8] an example for filtering is explained:

<p style="font-weight: bold;text-align: center;" alt="Example for filters on Amazon">
    If you’re looking to purchase a Nikon digital camera on Amazon,
    you don’t need to see products outside of electronics.
    Furthermore, you probably have a price range in mind. 
    If you’re an amateur photographer, you’re probably not interested in the $6,000 Nikon D4S.
</p>

When filtering is applied, either on low-cardinality fields or on ranges of numerical or date fields,
the search engine can drastically reduce the amount of documents which have to be searched.
E.g. If a filter range is given [Elasticsearch](#elasticsearch) (a lucene-based search engine) only searches in shards which could contain a matching document.
This means if a specific shard only contains documents where the price field has values above 50 and the query has a filter applied,
for the price field with the condition "price<50" the whole shard is ignored for this query[^9].
For lucene based search engines the filter mechanism does only work for fields which can not be queried with full text search. 
lucene has a different handling for these fields in comparison to the fields queried with a full text search.
See [Implementations](#implementations) for more information about search engines implementations.

Another feature of search engines is the facet search.
A facet search is often shown to the user for a low-cardinality field or only shows the top terms of a specific field.
Facet search allows the users to see how many results they would get if they would filter for the specific field value[^8].
This means for every shown value of the facet search field,
the search engine has to calculate the amount of documents it would return, 
if the user would filter for the specific field value.
Since the result set count for every facet value can be obtained by filtering,
the search engine can easily calculate the result for all facet values.
For lucene based search engines, this also means, facet search will not work for fields which use full text search.

## Ranking
The third key responsibility of a search engine is to rank and present the search results according to certain metrics 
which model how to best satisfy the users information needs[^3].
The example in section [Inverted index](#inverted-index) shows how a single document is obtained.
However in the case where several documents match, the search engine has to order the documents.
Usually, this order should represent the relevance of the document for the given search request.
One method to query with relevance is a boolean query, as shown in section [Boolean search](#boolean-search).

### Additional components in the inverted index
<!-- TODO image{5_Images/inverted_index_scoring.png}{Inverted index with scoring}[1.0]-->
The inverted index shown in the figure above contains two documents.
A query for "blue shoes" would match both documents, but the user would expect to get the first document as the top of the search results.
A search engine can accomplish the ranking by calculating a relevance score for each document.
This relevance score is calculated during the query by using additional components stored in the inverted index.
In the section [Inverted Index](#inverted-index) these components were listed.
Some of the listed properties are described in the following sections.
In this sections the example query for "blue shoes" and the inverted index shown in the first figure of section [Inverted Index](#inverted-index) are used.

#### Document frequency
For search results a document becomes more relevant if the given term is rare.
To calculate how many documents contain a specific term the "document frequency" is used[^10].
In the given example the document frequency for the term "like" is 2,
but the document frequency for the term "new" is 1.
The search results of a query for "new" OR "shoes" should list "Document 2" first,
because it contains both terms and the term "new" has a smaller document frequency and is therefore more relevant.

#### Term positions
The example query for "blue shoes" should return "Document 1" on the first position of the search results.
"Document 1" is more relevant, because it describes blue shoes.
"Document 2" also has the terms "blue" and "shoes", but it describes a blue dress and purple shoes.
The difference between the two documents is the distance between the terms.
In "Document 1" the term "blue" is on position 3 and the term "shoes" is on position 5, therefore the term distance is 1.
In "Document 2" the term "blue" is on position 4 and the term "shoes" is on position 9, therefore the term distance is 4.
In general a search engine assumes that a smaller term difference makes a document more relevant.
To calculate the difference the term positions for each term and document tuple is stored in the inverted index[^10].

### Sorting search results
A search engine is also capable of sorting the documents by a numeric value or an alphabetic string.
However this functionality is rarely used when executing full text queries, 
since the relevance sorting is much more important for the user[^11].

## Implementations
The discussed properties are used in lucene based search engines like 
[Elasticsearch](#elasticsearch) and 
[Apache Solr](#apache-solr).
Other search engines like Bleve[^12] can work in a similar way, but they do not have to.
The two systems (Solr and Elasticsearch) were isolated from the set of search engine solutions,
because all other inspected search engines lack on functionality compared to Solr and Elasticsearch[^13].

### Lucene

<p style="font-weight: bold;text-align: center;">
    "Apache Lucene is a modern, open source search library <br />designed to provide both relevant results as well as high performance."
</p>

The development of Apache Lucene was started in 1997 by Doug Cutting and was donated to the Apache Software Foundation in 2001[^14].
The implementation of Apache Lucene consists of two main components.
The first one is text analysis, implemented by a chain of analysis methods which produce a stream of tokens from the input data.
These tokens represent a collection of attributes. Besides the token value, there are attributes like token position, offsets, type etc.
which are part of the collection.
The second foundation is the indexing implementation.
Apache lucene uses the inverted index representation with additional functionality, as described in [Inverted index](#inverted-index).
For the inverted index implementation, a variety of encoding schemas is used.
The schemas affect the size of the index data and the cost of compression.
Lucene supports incremental updates by using the index extends (referred to as "segments").
These segments are periodically merged into larger segments, which minimizes the total number of index parts[^15].
Lucene is backed by a large community working to improve it.
It supports many enterprises in their commercial success and is also positioned well for experimental research work[^16].

### Apache Solr
Apache Solr is an open source enterprise search server.
It was written in Java and runs as a standalone full text search server.
For the cluster operation of Solr, an additional Zookeeper instance is needed.
Lucene is used for indexing and search functionalities.
Solr has a HTTP based API, which allows users or other programmes to interact with it.
The data is transmitted in XML, JSON, CSV, Javabin and more[^17].
A Solr server/cluster is a NoSQL Database with an eventual consistency guarantee[^18].
Therefore Solr will fulfill the consistency and partition tolerance guarantees,
but not the availability guarantee of the CAP-Theorem.
Solr is used in organizations such as Helprace, Jobreez, Apple, Inc., AT&T, AOL, reddit, etc. 
for search and facet browsing[^19].


One of the biggest advantages of Solr is the huge amount of functionality which is included in the default distribution.
This comes with the price of used disk space for the binary.
If the needed functionality is not included in the base distribution,
Solr allows to extend most of the functionality with plugins.
For the document processing a tight coupling of preprocessing, indexing and searching is used.
In comparison to Elasticsearch where a separate system (Logstash) can be used to pre-process documents.
This reduces the complexity of Elasticsearch, but increases the complexity for the overall system.
Therefore Solr tight coupling is an advantage for smaller systems, 
where the complexity should be as minimal as possible to reduce development and operation costs.

### Elasticsearch
Elasticsearch is also an open (source) enterprise search server.
It was written in Java and runs as a distributed full text search engine.
Elasticsearch is by default running as a cluster.
The nodes in the cluster can have different roles, 
such as master, data, ingest and machine learning.
If a cluster has only one node, this node has to have at least the master and data roles.
Elasticsearch provides a REST-like HTTP interface, which accepts and returns JSON documents,
scalable search, near real-time search and also supports multitenancy.
The cluster mode implementation of Elasticsearch will detect new or failed nodes automatically
and will reorganize the data distribution according to the new situation.
This and other features allow the users to scale Elasticsearch horizontally and
ensures resilient operations.
Similar to Solr, Elasticsearch is a NoSQL Database with an eventual consistency guarantee.
However according to Shay Banon, the founder of Elasticsearch, it gives up on partition tolerance
to guarantee consistency and availability[^20].
Elasticsearch is used by organizations, 
such as CERN[^21],  GitHub[^22], 
Stack Exchange[^23], Mozilla[^24], etc.


The main advantage for Elasticsearch in comparison to Solr is the cluster management.
While Elasticsearch has a build in cluster management, Solr needs Zookeeper to manage the cluster state.
Elasticsearch also has the ability to extend the core functionality with plugins.
In comparison to Solr, Elasticsearch offers an easier setup and use.
The REST-like API in combination with JSON documents are aligned with the current trend in the Web 2.0.
Since Elasticsearch uses the JSON documents also in it is query language,
the management of complex queries is much easier for the developers to handle.
The performance for search queries is also similar to Solr,
but the analytics performance is much better[^25].
The biggest disadvantage of Elasticsearch is the current licensing.
Before 15. January 2021 Elasticsearch was licensed under the Apache 2.0 license,
after this date (since version 7.11) the source code is licensed under SSPL,
which is not recognized as an open-source license by the open source initiative[^26].

<div style="color: green;text-weight: bold; text-align:center; font-size: 5em">
to be continued...
</div>

[^1]: Yue, Yisong and Patel, Rajan and Roehrig, Hein. Beyond position bias; 2010. 1013 p. Available from: [dl.acm.org](https://dl.acm.org/doi/abs/10.1145/1772690.1772793)
[^2]: Turnbull, Doug and Berryman, John. Relevant search: with applications for Solr and Elasticsearch. Manning; 2016. 18 p.
[^3]: Teofili, Tommaso and Mattmann, Chris. Deep learning for search. Manning; 2019. 14 p.
[^4]: Turnbull, Doug and Berryman, John. Relevant search: with applications for Solr and Elasticsearch. Manning; 2016. 23-25 p.
[^5]: El-Sappagh, Shaker H. Ali and Hendawi, Abdeltawab M. Ahmed and Bastawissy, Ali Hamed El. A proposed model for data warehouse ETL processes. 2011 91-104 p. Available from: [doi.org](https://doi.org/10.1016/j.jksuci.2011.05.005)
[^6]: Turnbull, Doug and Berryman, John. Relevant search: with applications for Solr and Elasticsearch. Manning; 2016. 32-33 p.
[^7]: Turnbull, Doug and Berryman, John. Relevant search: with applications for Solr and Elasticsearch. Manning; 2016. 34 p.
[^8]: Turnbull, Doug and Berryman, John. Relevant search: with applications for Solr and Elasticsearch. Manning; 2016. 36 p.
[^9]: Becciolini, Diego. Time range query performance 7.6. 2021 Available at: [discuss.elastic.co](https://discuss.elastic.co/t/time-range-query-performance-7-6/223194/4)
[^10]: Turnbull, Doug and Berryman, John. Relevant search: with applications for Solr and Elasticsearch. Manning; 2016. 24 p. table 2.1
[^11]: Turnbull, Doug and Berryman, John. Relevant search: with applications for Solr and Elasticsearch. Manning; 2016. 37 p.
[^12]: Bleve full-text search and indexing for Go. 2021. Available from: [blevesearch.com](https://blevesearch.com/)
[^13]: Luburić, Nikola and Ivanović, Dragan. Comparing Apache Solr and Elasticsearch search servers. 2016. Available from: [www.eventiotic.com](http://www.eventiotic.com/eventiotic/files/Papers/URL/icist2016_54.pdf)
[^14]: Białecki, Andrzej and Muir, Robert and Ingersoll, Grant. 2012. 1 p. Available from: [opensearchlab.otago.ac.nz](http://opensearchlab.otago.ac.nz/paper_10.pdf)
[^15]: Białecki, Andrzej and Muir, Robert and Ingersoll, Grant. 2012. 3 p. Available from: [opensearchlab.otago.ac.nz](http://opensearchlab.otago.ac.nz/paper_10.pdf)
[^16]: Białecki, Andrzej and Muir, Robert and Ingersoll, Grant. 2012. 7 p. Available from: [opensearchlab.otago.ac.nz](http://opensearchlab.otago.ac.nz/paper_10.pdf)
[^17]: Luburić, Nikola and Ivanović, Dragan. Comparing Apache Solr and Elasticsearch search servers. 2016. 2 p. Available from: [www.eventiotic.com](http://www.eventiotic.com/eventiotic/files/Papers/URL/icist2016_54.pdf)
[^18]: Kumar, Mukesh. SolrCloud : CAP theorem world, this makes Solr a CP system, and keep availability in certain circumstances. Head to Head; 2020. Available from: [ammozon.co.in](https://ammozon.co.in/headtohead/?p=188)
[^19]: PublicServers. 2019. Available from: [cwiki.apache.org](https://cwiki.apache.org/confluence/display/solr/PublicServers)
[^20]: Elastic. Elasticsearch and CAP Theorem. 2017. Available from: [discuss.elastic.co](https://discuss.elastic.co/t/cap-theorem/3014)
[^21]: Horanyi, Gergo. Needle in a haystack. 2014. Available from: [medium.com](https://medium.com/@ghoranyi/needle-in-a-haystack-873c97a99983)
[^22]: Pease, Tim. A Whole New Code Search. 2019. Available from: [github.blog](https://github.blog/2013-01-23-a-whole-new-code-search/)
[^23]: Nick Craver. What it takes to run Stack Overflow. 2013. Available from: [nickcraver.com](https://nickcraver.com/blog/2013/11/22/what-it-takes-to-run-stack-overflow/)
[^24]: Pedro Alves. Firefox 4, Twitter and NoSQL Elasticsearch. 2011. Available from: [pedroalves-bi.blogspot.com](http://pedroalves-bi.blogspot.com/2011/03/firefox-4-twitter-and-nosql.html)
[^25]: Luburić, Nikola and Ivanović, Dragan. Comparing Apache Solr and Elasticsearch search servers. 2016. 3-4 p. Available from: [www.eventiotic.com](http://www.eventiotic.com/eventiotic/files/Papers/URL/icist2016_54.pdf)
[^26]: FAQ on 2021 License Change. 2021. Available from: [www.elastic.co](https://www.elastic.co/pricing/faq/licensing)

