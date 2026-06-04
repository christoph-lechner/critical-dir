#!/usr/bin/env python3

from critical_dir.criticaldir_core import MyAnalyzer,MyPlotter,DataLoaderTestData,AlgoConfig

def run_test(ag: AlgoConfig):
    """
    Helper function for consistent preparation of test setup
    """
    my_dl = DataLoaderTestData()
    my_a = MyAnalyzer(dl=my_dl)

    # fixed dummy position in Hamburg for dev purposes
    my_pos = [53.55, 10.0]

    res = my_a.perform_analysis(
        observer_pos=my_pos,
        ag=ag
    )
    return res


def test_cluster1():
    # TEST: very small distance threshold and dropping of single-point clusters
    # -> expecting NO clusters
    res = run_test( AlgoConfig(exclude_isolated_points = True, cluster_dist_thres=0.1) )
    assert len(res.cluster_infos)==0

    # TEST: very small distance threshold and NOT dropping single-point clusters
    # -> expecting clusters
    res = run_test( AlgoConfig(exclude_isolated_points = False, cluster_dist_thres=0.1) )
    assert len(res.cluster_infos)>0
    assert len(res.cluster_infos)==len(res.data) # every data point is a single-element cluster

def test_cluster2():
    # TEST: distance threshold adjusted so that only one N=2 cluster should result and dropping single-point clusters
    # -> expecting one cluster
    res = run_test( AlgoConfig(exclude_isolated_points = True, cluster_dist_thres=2.0) )
    assert len(res.cluster_infos)==1

    # verify it is the expected N=2 cluster
    assert res.cluster_infos[0].N==2
