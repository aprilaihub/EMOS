"""Fast, offline structural checks for Information Unit and Feature contributions."""

import pytest

from ._checks import (
    FEATURE_ABSTRACT_METHODS,
    IU_KIND_INFO,
    REPO_ROOT,
    base_class_names,
    discover_feature_contributions,
    discover_iu_contributions,
    feature_class_name,
    feature_directory,
    find_class_node,
    first_parameter_name,
    inherits_from,
    iu_class_name,
    iu_directory,
    metadata_entries_for_feature,
    metadata_entries_for_iu,
    own_method_node,
    source_data_entries_for_feature,
    source_data_entries_for_iu,
)


IU_CONTRIBUTIONS = discover_iu_contributions()
FEATURE_CONTRIBUTIONS = discover_feature_contributions()


def _assert_required_files(directory, label):
    readme = directory / "README.md"
    assert readme.exists(), f"{label} is missing a README.md"
    assert readme.stat().st_size > 0, f"{label}/README.md is empty"
    assert (directory / "__init__.py").exists(), f"{label} is missing __init__.py"


@pytest.mark.unit
class TestContributionFolders:
    @pytest.mark.parametrize("kind,folder_name", IU_CONTRIBUTIONS)
    def test_iu_folder_has_required_files(self, kind, folder_name):
        _assert_required_files(iu_directory(kind, folder_name), f"{kind}/{folder_name}")

    @pytest.mark.parametrize("category,folder_name", FEATURE_CONTRIBUTIONS)
    def test_feature_folder_has_required_files(self, category, folder_name):
        _assert_required_files(feature_directory(category, folder_name), f"Features/{category}/{folder_name}")


@pytest.mark.unit
class TestContributionNaming:
    @pytest.mark.parametrize("kind,folder_name", IU_CONTRIBUTIONS)
    def test_iu_class_file_name(self, kind, folder_name):
        class_name = iu_class_name(kind, folder_name)
        assert (iu_directory(kind, folder_name) / f"{class_name}.py").exists(), f"Expected {class_name}.py in {kind}/{folder_name}"

    @pytest.mark.parametrize("category,folder_name", FEATURE_CONTRIBUTIONS)
    def test_feature_class_file_name(self, category, folder_name):
        class_name = feature_class_name(folder_name)
        assert (feature_directory(category, folder_name) / f"{class_name}.py").exists(), f"Expected {class_name}.py in Features/{category}/{folder_name}"


@pytest.mark.unit
class TestContributionMetadata:
    @pytest.mark.parametrize("kind,folder_name", IU_CONTRIBUTIONS)
    def test_iu_has_exactly_one_metadata_entry(self, kind, folder_name):
        entries = metadata_entries_for_iu(kind, folder_name)
        assert len(entries) == 1, f"{kind}/{folder_name} must have exactly one metadata entry"
        assert entries[0]["class_name"] == iu_class_name(kind, folder_name)

    @pytest.mark.parametrize("category,folder_name", FEATURE_CONTRIBUTIONS)
    def test_feature_has_exactly_one_metadata_entry(self, category, folder_name):
        entries = metadata_entries_for_feature(category, folder_name)
        assert len(entries) == 1, f"Features/{category}/{folder_name} must have exactly one metadata entry"
        assert entries[0]["class_name"] == feature_class_name(folder_name)


@pytest.mark.unit
class TestContributionSourceData:
    @pytest.mark.parametrize("kind,folder_name", IU_CONTRIBUTIONS)
    def test_iu_has_exactly_one_source_data_entry(self, kind, folder_name):
        entries = source_data_entries_for_iu(kind, folder_name)
        assert len(entries) == 1, f"{kind}/{folder_name} must have exactly one source_data.json entry"

    @pytest.mark.parametrize("category,folder_name", FEATURE_CONTRIBUTIONS)
    def test_feature_has_exactly_one_source_data_entry(self, category, folder_name):
        entries = source_data_entries_for_feature(category, folder_name)
        assert len(entries) == 1, f"Features/{category}/{folder_name} must have exactly one source_data.json entry"


@pytest.mark.unit
class TestContributionInterfaces:
    @pytest.mark.parametrize("kind,folder_name", IU_CONTRIBUTIONS)
    def test_iu_inherits_and_overrides_action(self, kind, folder_name):
        info = IU_KIND_INFO[kind]
        class_name = iu_class_name(kind, folder_name)
        file_path = iu_directory(kind, folder_name) / f"{class_name}.py"
        class_node = find_class_node(file_path, class_name)
        assert class_node is not None, f"Could not find class {class_name} in {file_path}"

        assert inherits_from(class_node, info["base_class"], REPO_ROOT / "Information_Units" / kind)
        method_node = own_method_node(class_node, info["action_method"])
        assert method_node is not None, f"{class_name} must override {info['action_method']}()"
        assert first_parameter_name(method_node) == info["action_param"]

    @pytest.mark.parametrize("category,folder_name", FEATURE_CONTRIBUTIONS)
    def test_feature_inherits_and_overrides_abstract_methods(self, category, folder_name):
        class_name = feature_class_name(folder_name)
        file_path = feature_directory(category, folder_name) / f"{class_name}.py"
        class_node = find_class_node(file_path, class_name)
        assert class_node is not None, f"Could not find class {class_name} in {file_path}"

        assert "BaseFeature" in base_class_names(class_node)
        for method_name in FEATURE_ABSTRACT_METHODS:
            assert own_method_node(class_node, method_name) is not None, f"{class_name} must override the abstract '{method_name}' method"