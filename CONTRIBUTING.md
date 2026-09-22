# Contributing to EMOS

You can contribute to EMOS in two ways:

1. [Information Units](#1-information-units)
2. [Features](#2-features)

## Before you start

Set up the project by following the instructions in [setup/README.md](setup/README.md).

Make one contribution at a time. This makes contributions easier to review.

## 1. Information Units

Information Units (IUs) provide information to EMOS. They can be:

- **Databases**, which find existing materials. For an example demo, refer to the [database IU tutorial](docs/user_guide/tutorial_database_iu.md).
- **Generators**, which create new materials. For an example demo, refer to the [generator IU tutorial](docs/user_guide/tutorial_generator_iu.md).
- **Predictors**, which calculate material properties. For an example demo, refer to the [predictor IU tutorial](docs/user_guide/tutorial_predictor_iu.md).

To add an IU:

1. Add the IU basic information to `devtools/source_data.json`.
2. Create an IU code template by running `python devtools/contribution_tool.py`.
3. Update the Python implementation and property mapping in the generated template.
4. Add the IU panel by running `python devtools/iu_features/manage_iu_features.py`.
5. Add proper documentation to the IU README and test your contribution.

## 2. Features

Features give users tools for exploring materials and using EMOS capabilities. Read the [feature tutorial](docs/user_guide/tutorial_feature.md) for an example demo.

To add a feature:
 
1. Add your feature to `devtools/source_data.json`.
2. Run `python devtools/contribution_tool.py`.
3. Complete the generated Python and JavaScript code.
4. Test your feature and update its README.

## Submitting

Before opening a pull request:

- Make sure your code and tests work.
- Update the README for your IU or feature.
- Include any setup instructions or required dependencies.
- Explain what your contribution does.

Thank you for contributing to EMOS.
