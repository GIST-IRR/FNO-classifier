import random
import numpy as np
import torch
import os
from pathlib import Path

def fix_seed(
        seed: int,
        python_seed: bool=True,
        numpy_seed: bool=True,
        torch_seed: bool=True,
        cuda_seed: bool=True,
        worker_init_fn: bool=True,
        generator: bool=True,
        deterministic: bool=True,
        benchmark: bool=False,
        work_space_config: str=":16:8"
    ):
    """If you want to fix seed, you have to call this function before assigning
    variables that you want to fix.

    Args:
        seed (int): A random seed that used to fix all seeds.
        python_seed (bool, optional): Fix python random. Defaults to True.
        numpy_seed (bool, optional): Fix numpy random. Defaults to True.
        torch_seed (bool, optional): Fix pytorch random. Defaults to True.
        cuda_seed (bool, optional): Fix CUDA random. Defaults to True.
        worker_init_fn (bool, optional): Return worker_init_fn if True. Defaults to False.
        generator (bool, optional): Return generator if True. Defaults to False.
        deterministic (bool, optional): Set deterministic. Defaults to True.
        benchmark (bool, optional): Set benchmark. Defaults to False.
        work_space_config (_type_, optional): Set work space config. Defaults to ":16:8".

    Returns:
        _type_: _description_
    """
    # Python
    if python_seed:
        random.seed(seed)
    # Numpy
    if numpy_seed:
        np.random.seed(seed)
    # if you turn off funcs below, model is random, loader is fixed.
    # Pytorch
    if torch_seed:
        torch.manual_seed(seed)
        torch.backends.cudnn.deterministic = deterministic
        torch.backends.cudnn.benchmark = benchmark
    # CUDA
    if cuda_seed:
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        if torch.version.cuda >= str(10.2):
            os.environ['CUBLAS_WORKSPACE_CONFIG']=work_space_config
            # or ":4096:2"
        else:
            os.environ['CUDA_LAUNCH_BLOCKING']="1"

    if worker_init_fn:
        def seed_worker(worker_id):
            worker_seed = seed % 2**32
            random.seed(worker_seed)
            np.random.seed(worker_seed)
        worker_init_fn = seed_worker
    else:
        worker_init_fn = None
    
    if generator:
        generator = torch.Generator()
        generator.manual_seed(seed)
    else:
        generator = None

    return worker_init_fn, generator

def save(
        save_name,
        reproducible=True,
        **checkpoint
    ):
    # checkpoint = {
    #     'model': model.state_dict(),
    #     'optimizer': optimizer.state_dict()
    # }
    #     
    # if scheduler is not None:
    #     checkpoint.update({'scheduler': scheduler.state_dict()})

    if reproducible:
        checkpoint.update({
            'random.python': random.getstate(),
            'random.numpy': np.random.get_state(),
            'random.torch': torch.random.get_rng_state(),
            'random.cuda': torch.cuda.get_rng_state(),
            'random.cuda_all': torch.cuda.get_rng_state_all(),
        })

    torch.save(checkpoint, save_name)

def load(
        filename,
        reproducible=True,
        worker_init_fn=True,
        generator=True,
    ):
    # Load checkpoint
    if not isinstance(filename, Path):
        filename = Path(filename)
    with filename.open('rb') as f:
        checkpoint = torch.load(f)

    # # Load model
    # model.load_state_dict(checkpoint.pop('model'))
    # optimizer.load_state_dict(checkpoint.pop('optimizer'))
    
    # if scheduler is not None:
    #     try:
    #         scheduler.load_state_dict(checkpoint.pop('scheduler'))
    #     except:
    #         print("Warning: scheduler is not loaded.")

    if reproducible:
        try:
            random.setstate(checkpoint['random.python'])
            np.random.set_state(checkpoint['random.numpy'])
            torch.random.set_rng_state(checkpoint['random.torch'])
            torch.cuda.set_rng_state(checkpoint['random.cuda'])
            torch.cuda.set_rng_state_all(checkpoint['random.cuda_all'])

            if worker_init_fn:
                def seed_worker(worker_id):
                    random.setstate(checkpoint['random.python'])
                    np.random.set_state(checkpoint['random.numpy'])
                worker_init_fn = seed_worker

            if generator:
                generator = torch.Generator()
                generator.set_state(checkpoint['random.torch'].cpu())
        except:
            print("Warning: reproducible is not loaded.")

    if worker_init_fn:
        checkpoint.update({"worker_init_fn": worker_init_fn})
    if generator:
        checkpoint.update({"generator": generator})
        
    return checkpoint

