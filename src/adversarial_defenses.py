import numpy as np

def remove_outliers_defense(model, x, params):
    top_k = params["top_k"]
    num_std = params["num_std"]

    dists = x[np.newaxis, :, :] - x[:, np.newaxis, :]
    dists = np.linalg.norm(dists, axis = 2)

    dists = np.where(np.eye(len(x)) > 0.0, np.full(dists.shape, np.inf), dists)
    dists = np.sort(dists, axis = 1)[:, :top_k]
    dists = np.mean(dists, axis = 1)

    avg = np.mean(dists)
    std = num_std * np.std(dists)

    remove = dists > avg + std
    idx = np.argmin(remove)
    x[remove] = x[idx]

    return x

def remove_salient_defense(model, x, params):
    top_k = params["top_k"]

    grads = model.output_grad_fn(x)
    norms = np.linalg.norm(grads, axis = 2)
    norms = np.max(grads, axis = 0)
    remove = np.argsort(norms)[-top_k:]

    mask = np.zeros(len(x))
    mask[remove] = 1.0
    idx = np.argmin(mask)
    x[remove] = x[idx]

    return x
