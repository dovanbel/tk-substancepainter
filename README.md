
# ShotGrid Toolkit Engine for Adobe Substance 3D Painter

A ShotGrid engine for Adobe Substance 3D Painter that enables seamless integration with your VFX/animation pipeline.

## Features

- **Project Management**: Create and manage Substance Painter projects through the Shotgun Workfiles app
- **Publishing**: Publish both `.spp` project files and exported texture sets to Shotgun
- **Multi-App Support**: Integrates with standard Shotgun apps (Workfiles2, Publisher, Breakdown, etc.)

## Requirements

- Adobe Substance 3D Painter (version 12 or higher recommended)
- Shotgun Toolkit
- Python 3.7+
- A configured Shotgun pipeline (based on `tk-config-default2`)

## Installation

Add the engine location to your pipeline configuration in `env/includes/engine_locations.yml`:

```yaml
engines.tk-substancepainter.location:
  type: git
  path: https://github.com/dovanbel/tk-substancepainter.git
  version: v1.0.1 # Update to the latest available tag from this repo
```

## Configuration

The following sections provide configuration examples for a pipeline based on [tk-config-default2](https://github.com/shotgunsoftware/tk-config-default2). Customize these to fit your studio's needs.

### Templates Configuration

Add these template definitions to `core/templates.yml`:

```yaml

    ##################### keys section

    texture_extension:
        type: str
        filter_by: alphanumeric
        alias: extension

    ##################### templates section


    asset_root: Assets/{sg_asset_type}/{Asset}/{Step}
    
    substancepainter_asset_root: '@asset_root/substancepainter'

    substancepainter_asset_project_work_area:
        definition: '@substancepainter_asset_root/projects/work'
    substancepainter_asset_project_publish_area:
        definition: '@substancepainter_asset_root/projects/publish'
    substancepainter_asset_texture_work_area:
        definition: '@substancepainter_asset_root/export/work'
    substancepainter_asset_texture_publish_area:
        definition: '@substancepainter_asset_root/export/publish'

    # WIP project files
    substancepainter_asset_work:
        definition: '@substancepainter_asset_project_work_area/{Asset}_{task_name}_{name}_v{version}.spp'
    
    # Published Substance Painter project files
    substancepainter_asset_publish:
        definition: '@substancepainter_asset_project_publish_area/{Asset}_{task_name}_{name}_v{version}.spp'
    
    # Project snapshots
    substancepainter_asset_snapshot:
        definition: '@substancepainter_asset_project_work_area/snapshots/{Asset}_{task_name}_{name}_v{version}_{timestamp}.spp'
    
    # Published texture files
    substancepainter_asset_texture_publish:
        definition: '@substancepainter_asset_texture_publish_area/{texture_set}_v{version}/{Asset}_{task_name}_{texture_set}_{texture_map}_{colorspace}_v{version}.{texture_extension}'
    
    # Published UDIM texture files
    substancepainter_asset_texture_udim_publish:
        definition: '@substancepainter_asset_texture_publish_area/{texture_set}_v{version}/{Asset}_{task_name}_{texture_set}_{texture_map}_{colorspace}_v{version}.{UDIM}.{texture_extension}'
    
    # Texture set publish folder
    substancepainter_asset_texture_set_publish:
        definition: '@substancepainter_asset_texture_publish_area/{texture_set}_v{version}'
```

### Software Paths

Define application paths in `env/includes/software_paths.yml`:

```yaml
# Substance Painter
path.linux.substancepainter: '/opt/Adobe/Adobe_Substance_3D_Painter'
path.mac.substancepainter: '/Applications/Adobe Substance 3D Painter.app'
path.windows.substancepainter: 'C:\Program Files\Adobe\Adobe Substance 3D Painter\Adobe Substance 3D Painter.exe'
```

### Launch App Configuration

Configure the launcher in `env/includes/settings/tk-multi-launchapp.yml`:

```yaml
# Substance Painter
settings.tk-multi-launchapp.substancepainter:
  engine: tk-substancepainter
  linux_path: "@path.linux.substancepainter"
  mac_path: "@path.mac.substancepainter"
  windows_path: "@path.windows.substancepainter"
  menu_name: "Substance Painter"
  location: "@apps.tk-multi-launchapp.location"
```

### Environment Configuration

#### Project Environment

Add to `env/project.yml`:

```yaml
includes:
- ./includes/settings/tk-substancepainter.yml

engines:
  tk-substancepainter: "@settings.tk-substancepainter.project"
```

#### Asset Step Environment

Add to `env/asset_step.yml`:

```yaml
includes:
- ./includes/settings/tk-substancepainter.yml

engines:
  tk-substancepainter: "@settings.tk-substancepainter.asset_step"
```

### App-Specific Settings

#### Breakdown Configuration

In `env/includes/settings/tk-multi-breakdown2.yml`:

```yaml
settings.tk-multi-breakdown2.substancepainter:
  hook_scene_operations: "{engine}/tk-multi-breakdown2/tk-substancepainter_scene_operations.py"
  panel_mode: False
  published_file_filters: []
  location: "@apps.tk-multi-breakdown2.location"
```

#### Loader Configuration

In `env/includes/settings/tk-multi-loader2.yml`:

```yaml
settings.tk-multi-loader2.substancepainter:
  actions_hook: "{engine}/tk-multi-loader2/tk-substancepainter_actions.py"
  entities:
  - caption: Current Project
    type: Hierarchy
    root: "{context.project}"
    publish_filters: []
  - caption: My Tasks
    type: Query
    entity_type: Task
    filters:
    - [project, is, '{context.project}']
    - [task_assignees, is, '{context.user}']
    hierarchy: [entity, content]
  publish_filters: [["sg_status_list", "is_not", null]]
  location: "@apps.tk-multi-loader2.location"
```

#### Publisher Configuration

In `env/includes/settings/tk-multi-publish2.yml`:

```yaml
# Substance Painter - Asset Step
settings.tk-multi-publish2.substancepainter.asset_step:
  collector: "{self}/collector.py:{engine}/tk-multi-publish2/basic/collector.py"
  collector_settings:
      Work Template: substancepainter_asset_work
  publish_plugins:
  - name: Publish Project to ShotGrid
    hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_session.py"
    settings:
        Publish Template: substancepainter_asset_publish
  - name: Publish Textures to ShotGrid
    hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_texture_set.py"
    settings:
      Publish Template: substancepainter_asset_texture_publish
      Publish UDIM Template: substancepainter_asset_texture_udim_publish
      Publish Folder Template: substancepainter_asset_texture_set_publish
  location: "@apps.tk-multi-publish2.location"
```

#### Shotgun Panel Configuration

In `env/includes/settings/tk-multi-shotgunpanel.yml`:

```yaml
settings.tk-multi-shotgunpanel.substancepainter:
  action_mappings:
    PublishedFile:
    - actions: [publish_clipboard]
      filters: {}
    Task:
    - actions: [assign_task, task_to_ip]
      filters: {}
    Version:
    - actions: [quicktime_clipboard, sequence_clipboard, add_to_playlist]
      filters: {}
  location: "@apps.tk-multi-shotgunpanel.location"
```

#### Workfiles Configuration

In `env/includes/settings/tk-multi-workfiles2.yml`:

```yaml
# Substance Painter - Project Context
settings.tk-multi-workfiles2.substancepainter.project:
  hook_scene_operation: "{engine}/tk-multi-workfiles2/scene_operation_tk-substancepainter.py"
  allow_task_creation: True
  create_new_task_hook: "{self}/create_new_task.py"
  custom_actions_hook: "{self}/custom_actions.py"
  auto_expand_tree: True
  entities:
  - caption: Assets
    entity_type: Task
    filters:
    - [entity, type_is, Asset]
    - [step.Step.code, is, "texturing"]
    hierarchy: [entity.Asset.sg_asset_type, entity, content]
  location: "@apps.tk-multi-workfiles2.location"

# Substance Painter - Asset Step Context
settings.tk-multi-workfiles2.substancepainter.asset_step:
  allow_task_creation: False
  saveas_default_name: main
  auto_expand_tree: True
  custom_actions_hook: "{self}/custom_actions.py"
  hook_copy_file: "{self}/copy_file.py"
  hook_filter_publishes: default
  hook_filter_work_files: default
  hook_scene_operation: "{engine}/tk-multi-workfiles2/scene_operation_tk-substancepainter.py"
  template_publish: substancepainter_asset_publish
  template_publish_area: substancepainter_asset_project_publish_area
  template_work: substancepainter_asset_work
  template_work_area: substancepainter_asset_project_work_area
  entities:
  - caption: Assets
    entity_type: Task
    filters:
    - [entity, type_is, Asset]
    - [step.Step.code, is, "texturing"]
    hierarchy: [entity.Asset.sg_asset_type, entity, content]
  file_extensions: []
  location: "@apps.tk-multi-workfiles2.location"
```

#### Engine Settings

Create `env/includes/settings/tk-substancepainter.yml`:

```yaml
################################################################################

includes:
- ../app_locations.yml
- ../engine_locations.yml
- ./tk-multi-breakdown2.yml
- ./tk-multi-loader2.yml
- ./tk-multi-publish2.yml
- ./tk-multi-shotgunpanel.yml
- ./tk-multi-workfiles2.yml

################################################################################

# Project Context
settings.tk-substancepainter.project:
  compatibility_dialog_min_version: 12
  textures_export_work_area: substancepainter_asset_texture_work_area
  modeling_root_area: asset_root
  modeling_step_name: modeling
  windows_path_mappings:
    - unc_prefix: '\\yourserver\projects'
      mapped_drive_prefix: 'X:\projects'
  apps:
    tk-multi-about:
      location: "@apps.tk-multi-about.location"
    tk-multi-shotgunpanel: "@settings.tk-multi-shotgunpanel.substancepainter"
    tk-multi-workfiles2: "@settings.tk-multi-workfiles2.substancepainter.project"
    tk-multi-pythonconsole:
      location: "@apps.tk-multi-pythonconsole.location"
  menu_favourites:
  - {app_instance: tk-multi-workfiles2, name: File Open...}
  location: "@engines.tk-substancepainter.location"

# Asset Step Context
settings.tk-substancepainter.asset_step:
  compatibility_dialog_min_version: 12
  textures_export_work_area: substancepainter_asset_texture_work_area
  modeling_root_area: asset_root
  modeling_step_name: modeling
  windows_path_mappings: []
  apps:
    tk-multi-about:
      location: "@apps.tk-multi-about.location"
    tk-multi-loader2: "@settings.tk-multi-loader2.substancepainter"
    tk-multi-publish2: "@settings.tk-multi-publish2.substancepainter.asset_step"
    tk-multi-shotgunpanel: "@settings.tk-multi-shotgunpanel.substancepainter"
    tk-multi-workfiles2: "@settings.tk-multi-workfiles2.substancepainter.asset_step"
    tk-multi-breakdown2: "@settings.tk-multi-breakdown2.substancepainter"
    tk-multi-pythonconsole:
      location: "@apps.tk-multi-pythonconsole.location"
  menu_favourites:
  - {app_instance: tk-multi-workfiles2, name: File Open...}
  - {app_instance: tk-multi-workfiles2, name: File Save...}
  - {app_instance: tk-multi-publish2, name: Publish...}
  location: "@engines.tk-substancepainter.location"
```

## Usage

### Getting Started

1. Launch Substance Painter from Shotgun Desktop
2. The engine will initialize and display the Shotgun menu in the application

### Creating a New Project

1. Select **File Open** from the Shotgun menu
2. The Workfiles app will open
3. Navigate to the texturing task for your asset
4. Click **+ New File**
5. Configure the "New Substance Project" dialog:
   - Select the mesh to texture
   - Choose a Substance Painter template (optional)
   - Set document resolution
   - Configure normal map format
   - Set tangent space calculation method
   - Enable UV Tiles (UDIMs) if needed (⚠️ **cannot be changed later**)
6. Save your project using **File Save** from the Shotgun menu

### Scene Breakdown

The Scene Breakdown app (`tk-multi-breakdown2`) monitors your project's mesh references and will allow you to update the mesh

### Loader

**Note:** The Loader app is configured but not implemented in v1.0.1. The configuration is required as `tk-multi-breakdown2` depends on it.

### Publishing

The Publisher handles two types of publishes:

#### 1. Project File Publishing

Publishes the `.spp` project file to Shotgun, similar to standard session publishing in other DCCs.

#### 2. Texture Publishing

Exports and publishes texture sets.

#### Export Preset System

Due to limitations in the Substance Painter Python API, this engine uses a custom export preset workflow:

**How It Works:**

1. **Base Preset**: The engine includes a "Shotgrid_base" export preset (located in `resources/export-presets/`)
2. **Auto-Installation**: On first launch of the engine, this preset is copied to your Substance Painter documents directory
3. **Preservation**: The engine won't overwrite existing presets, allowing you to customize them
4. **Naming Convention**: Use presets starting with "Shotgrid..." to make them available for publishing

**Required Filename Pattern for all texture maps:**

```
$textureSet_<MapName>_$colorSpace(.$udim)
```

Where:
- `$textureSet` - Substance Painter variable for texture set name
- `<MapName>` - Your custom map name (e.g., BaseColor, Roughness, Normal)
  - ⚠️ **Do not use spaces or underscores in map names**
- `$colorSpace` - Substance Painter variable for color space
- `(.$udim)` - Optional UDIM suffix for tiled workflows

**Customization:**

- Add additional texture maps to the "Shotgrid_base" preset as needed
- Duplicate the preset to create variations (ensure the name starts with "Shotgrid")
- Select your preferred preset from the dropdown in the Publisher UI

**Publishing Process:**

1. **Validation**: Checks that filename patterns match the required format
2. **Export**: Textures are exported to a work folder using the selected preset
3. **Publishing**: Files are copied and renamed according to the publish template to the publish location with version numbers
4. **Database**: Each texture map is registered as a PublishedFile in Shotgun
5. **Texture Set**: A parent PublishedFile is created linking all texture maps together

The published texture set can be used downstream in other DCCs (e.g., automatically assigning textures to shader slots in Maya via a custom loader action).

## Known Issues and Limitations

### Platform Support
- **Tested on**: Windows only
- **Untested**: macOS and Linux (configuration provided but requires validation)

### UI Styling
There are visual issues with app interfaces in v1.0.1:
- Some buttons appear overly bright
- Font readability issues in certain dialogs
- Similar to historical issues with `tk-houdini`

Contributions to resolve these styling issues are welcome!

### Loader Implementation
The Loader app is not fully implemented. To add functionality:
- Explore the `substance_painter.resource` module in the Python API
- Implement custom loader actions as needed

### Software Entity System
- The provided configuration uses YAML-based software paths
- Software Entity system (defining paths in Shotgun) is untested but should work

## Testing and Stability

⚠️ **Version v1.0.1 is freshly released**
- Expect potential bugs and edge cases
- Test thoroughly in a development environment before production use
- Report issues on the [GitHub repository](https://github.com/dovanbel/tk-substancepainter/issues)

## Contributing

Contributions are welcome! Areas where help would be particularly valuable:
- UI styling fixes
- macOS and Linux testing
- Loader app implementation
- Documentation improvements


## Acknowledgments

A big thanks to Diego Garcia Huerta, whose tk-substancepainter engine was my starting point
(https://github.com/diegogarciahuerta/tk-substancepainter)


## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
