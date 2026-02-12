import os
import tempfile
from pymatgen.core import Structure, Lattice
from Information_Units.Databases.BaseDatabase import BaseDatabase


class AflowlibDatabase(BaseDatabase):
    """AFLOWLIB database implementation"""
    
    def __init__(self, database_name='aflowlib', logger=None):
        super().__init__(database_name, logger)
        self.output_dir = tempfile.mkdtemp(prefix="aflowlib_")
    
    def info(self):
        return "AFLOWLIB: Automatic-FLOW database for high-throughput materials discovery"

    def retrieve(self, inputs: dict) -> list:
        """
        Retrieve materials from AFLOWLIB and save as CIF files.
        
        Args:
            inputs (dict): Query parameters
                - query: Material query (e.g., 'Fe', 'Al2O3')
                - limit: Max number of results (default: 10)
        
        Returns:
            list: Paths to saved CIF files
        """
        try:
            query = inputs.get('query', '')
            limit = inputs.get('limit', 10)
            
            if self.logger:
                self.logger.log(f"Retrieving from AFLOWLIB: {query} (limit: {limit})")
            
            # Get sample structures (can be replaced with real API calls later)
            structures = self._get_sample_structures(query, limit)
            
            # Save as CIF files
            cif_paths = []
            for i, struct in enumerate(structures):
                cif_path = self._save_cif(struct, i)
                if cif_path:
                    cif_paths.append(cif_path)
                    if self.logger:
                        self.logger.log(f"Saved: {cif_path}")
            
            return cif_paths
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error: {str(e)}")
            return []
    
    def _get_sample_structures(self, query: str, limit: int):
        """Get sample structures for demonstration"""
        
        # Sample AFLOWLIB-like structures
        samples = [
            {
                'name': 'Fe-bcc',
                'lattice': [[2.87, 0, 0], [0, 2.87, 0], [0, 0, 2.87]],
                'species': ['Fe', 'Fe'],
                'coords': [[0, 0, 0], [0.5, 0.5, 0.5]]
            },
            {
                'name': 'Al2O3',
                'lattice': [[4.765, 0, 0], [0, 4.765, 0], [0, 0, 12.99]],
                'species': ['Al', 'Al', 'O', 'O', 'O'],
                'coords': [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5], 
                           [0.3, 0.3, 0.2], [0.7, 0.7, 0.2], [0.0, 0.5, 0.0]]
            },
            {
                'name': 'Fe2O3',
                'lattice': [[3.03, 0, 0], [0, 3.03, 0], [0, 0, 5.04]],
                'species': ['Fe', 'Fe', 'O', 'O', 'O'],
                'coords': [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5],
                           [0.3, 0.3, 0.25], [0.7, 0.7, 0.25], [0.0, 0.5, 0.0]]
            }
        ]
        
        # Filter by query if specified
        if query and query.lower() != 'all':
            samples = [s for s in samples if query.lower() in s['name'].lower()]
        
        # Limit results
        return samples[:limit]
    
    def _save_cif(self, struct_dict: dict, index: int) -> str:
        """Save structure as CIF file"""
        try:
            # Create pymatgen Structure
            lattice = Lattice(struct_dict['lattice'])
            structure = Structure(
                lattice=lattice,
                species=struct_dict['species'],
                coords=struct_dict['coords'],
                coords_are_cartesian=False
            )
            
            # Save CIF
            filename = f"{struct_dict['name']}_{index}.cif"
            filepath = os.path.join(self.output_dir, filename)
            structure.to(filename=filepath, fmt='cif')
            
            return filepath
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error saving CIF: {str(e)}")
            return None