curl "http://localhost:8081/clusters?maxdist=2&exclstat=0"
-> no clusters found

curl "http://localhost:8081/clusters?maxdist=2.5&exclstat=0"
-> returns one N=3 cluster (as expected)
