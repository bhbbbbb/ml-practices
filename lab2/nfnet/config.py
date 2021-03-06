from imgclf.config import Config

class NfnetConfig(Config):
    amp = False        # Enable automatic mixed precision

    # Model
    variant = 'F1'         # F0 - F7
    num_class = 15     # Number of classes
    activation = 'gelu'    # or 'relu'
    stochdepth_rate = 0.25 # 0-1, the probability that a layer is dropped during one step
    alpha = 0.2            # Scaling factor at the end of each block
    se_ratio = 0.5         # Squeeze-Excite expansion ratio
    use_fp16 = False       # Use 16bit floats, which lowers memory footprint. This currently sets
                        # the complete model to FP16 (will be changed to match FP16 ops from paper)

    # Training
    # batch_size = 64        # Batch size
    # epochs = 360           # Number of epochs
    overfit = False        # Train on one batch size only

    # learning_rate = 0.1    # Learning rate
    # scale_lr = True        # Scale learning rate with batch size. lr = lr*batch_size/256
    momentum = 0.9         # Contribution of earlier gradient to gradient update
    weight_decay = 0.00002 # Factor with which weights are added to gradient
    nesterov = True        # Enable nesterov correction

    do_clip = True         # Enable adaptive gradient clipping
    clipping = 0.1         # Adaptive gradient clipping parameter

    epochs_per_checkpoint: int = 1
