"""
Unit tests for intent merging logic.
"""
import yaml
from pathlib import Path

from ops_translate.intent.merge import smart_merge, detect_conflicts


def test_smart_merge_combines_inputs():
    """Test smart merge combines input parameters from multiple intents"""
    intents = [
        {
            'file': 'file1.yaml',
            'data': {
                'intent': {
                    'workflow_name': 'test',
                    'workload_type': 'virtual_machine',
                    'inputs': {
                        'vm_name': {
                            'type': 'string',
                            'required': True
                        },
                        'environment': {
                            'type': 'enum',
                            'values': ['dev', 'prod'],
                            'required': True
                        }
                    }
                }
            }
        },
        {
            'file': 'file2.yaml',
            'data': {
                'intent': {
                    'workflow_name': 'test',
                    'workload_type': 'virtual_machine',
                    'inputs': {
                        'vm_name': {
                            'type': 'string',
                            'required': True
                        },
                        'environment': {
                            'type': 'enum',
                            'values': ['dev', 'staging'],
                            'required': False
                        },
                        'memory_gb': {
                            'type': 'integer',
                            'required': False,
                            'default': 8
                        }
                    }
                }
            }
        }
    ]

    merged = smart_merge(intents)

    # Verify inputs are merged
    assert 'inputs' in merged['intent']
    inputs = merged['intent']['inputs']

    # All unique inputs should be present
    assert 'vm_name' in inputs
    assert 'environment' in inputs
    assert 'memory_gb' in inputs

    # Environment should have combined enum values
    assert set(inputs['environment']['values']) == {'dev', 'prod', 'staging'}

    # Required should be True (stricter wins)
    assert inputs['environment']['required'] == True


def test_smart_merge_combines_approvers():
    """Test smart merge combines approver lists"""
    intents = [
        {
            'file': 'file1.yaml',
            'data': {
                'intent': {
                    'governance': {
                        'approval': {
                            'required_when': {'environment': 'prod'},
                            'approvers': ['ops-team']
                        }
                    }
                }
            }
        },
        {
            'file': 'file2.yaml',
            'data': {
                'intent': {
                    'governance': {
                        'approval': {
                            'required_when': {'environment': 'prod'},
                            'approvers': ['dba-team', 'security-team']
                        }
                    }
                }
            }
        }
    ]

    merged = smart_merge(intents)

    # Verify approvers are combined
    approvers = merged['intent']['governance']['approval']['approvers']
    assert set(approvers) == {'dba-team', 'ops-team', 'security-team'}


def test_smart_merge_uses_most_restrictive_quotas():
    """Test smart merge uses minimum quota values"""
    intents = [
        {
            'file': 'file1.yaml',
            'data': {
                'intent': {
                    'governance': {
                        'quotas': {
                            'max_cpu': 16,
                            'max_memory_gb': 64
                        }
                    }
                }
            }
        },
        {
            'file': 'file2.yaml',
            'data': {
                'intent': {
                    'governance': {
                        'quotas': {
                            'max_cpu': 32,
                            'max_memory_gb': 128
                        }
                    }
                }
            }
        }
    ]

    merged = smart_merge(intents)

    # Verify most restrictive (minimum) values used
    quotas = merged['intent']['governance']['quotas']
    assert quotas['max_cpu'] == 16  # min(16, 32)
    assert quotas['max_memory_gb'] == 64  # min(64, 128)


def test_smart_merge_uses_max_compute():
    """Test smart merge uses maximum compute values"""
    intents = [
        {
            'file': 'file1.yaml',
            'data': {
                'intent': {
                    'compute': {
                        'cpu_cores': 4,
                        'memory_gb': 16,
                        'disk_gb': 100
                    }
                }
            }
        },
        {
            'file': 'file2.yaml',
            'data': {
                'intent': {
                    'compute': {
                        'cpu_cores': 8,
                        'memory_gb': 32,
                        'disk_gb': 200
                    }
                }
            }
        }
    ]

    merged = smart_merge(intents)

    # Verify maximum values used
    compute = merged['intent']['compute']
    assert compute['cpu_cores'] == 8  # max(4, 8)
    assert compute['memory_gb'] == 32  # max(16, 32)
    assert compute['disk_gb'] == 200  # max(100, 200)


def test_smart_merge_uses_mixed_for_different_workload_types():
    """Test smart merge uses 'mixed' when workload types differ"""
    intents = [
        {
            'file': 'file1.yaml',
            'data': {
                'intent': {
                    'workload_type': 'virtual_machine'
                }
            }
        },
        {
            'file': 'file2.yaml',
            'data': {
                'intent': {
                    'workload_type': 'container'
                }
            }
        }
    ]

    merged = smart_merge(intents)

    assert merged['intent']['workload_type'] == 'mixed'


def test_smart_merge_combines_metadata():
    """Test smart merge combines tags and labels"""
    intents = [
        {
            'file': 'file1.yaml',
            'data': {
                'intent': {
                    'metadata': {
                        'tags': [
                            {'key': 'application', 'value': 'web'},
                            {'key': 'tier', 'value': 'frontend'}
                        ],
                        'labels': {
                            'managed-by': 'ops-translate'
                        }
                    }
                }
            }
        },
        {
            'file': 'file2.yaml',
            'data': {
                'intent': {
                    'metadata': {
                        'tags': [
                            {'key': 'application', 'value': 'database'},
                            {'key': 'backup', 'value': 'enabled'}
                        ],
                        'labels': {
                            'managed-by': 'ops-translate',
                            'backup-policy': 'daily'
                        }
                    }
                }
            }
        }
    ]

    merged = smart_merge(intents)

    metadata = merged['intent']['metadata']

    # Tags should be combined by key (first wins for duplicates)
    tags = metadata['tags']
    tag_keys = [t['key'] for t in tags]
    assert 'application' in tag_keys
    assert 'tier' in tag_keys
    assert 'backup' in tag_keys

    # Labels should be union
    labels = metadata['labels']
    assert labels['managed-by'] == 'ops-translate'
    assert labels['backup-policy'] == 'daily'


def test_detect_conflicts_no_false_positives():
    """Test conflict detection doesn't report identical values as conflicts"""
    # Create temp intent files with identical workflow names
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        file1 = tmpdir / "file1.intent.yaml"
        file2 = tmpdir / "file2.intent.yaml"

        intent_data = {
            'intent': {
                'workflow_name': 'same_name',
                'workload_type': 'virtual_machine'
            }
        }

        file1.write_text(yaml.dump(intent_data))
        file2.write_text(yaml.dump(intent_data))

        conflicts = detect_conflicts([file1, file2])

        # Should not report workflow_name or workload_type as conflicts
        conflict_text = '\n'.join(conflicts)
        assert 'Workflow Name Conflict' not in conflict_text
        assert 'Workload Type Conflict' not in conflict_text


def test_detect_conflicts_reports_real_differences():
    """Test conflict detection reports actual differences"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        file1 = tmpdir / "file1.intent.yaml"
        file2 = tmpdir / "file2.intent.yaml"

        file1.write_text(yaml.dump({
            'intent': {
                'workflow_name': 'name1',
                'compute': {'cpu_cores': 4}
            }
        }))

        file2.write_text(yaml.dump({
            'intent': {
                'workflow_name': 'name2',
                'compute': {'cpu_cores': 8}
            }
        }))

        conflicts = detect_conflicts([file1, file2])

        # Should report workflow_name and compute conflicts
        conflict_text = '\n'.join(conflicts)
        assert 'Workflow Name Conflict' in conflict_text
        assert 'Compute Resource Conflicts' in conflict_text
        assert 'cpu_cores' in conflict_text
