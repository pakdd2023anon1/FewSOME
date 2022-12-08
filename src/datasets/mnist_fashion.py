import torch.utils.data as data
from PIL import Image
from torchvision.datasets.utils import download_and_extract_archive, extract_archive, verify_str_arg, check_integrity
import torch
import random
import os
import codecs
import numpy as np
import random

class FASHION(data.Dataset):


    mirrors = ["http://fashion-mnist.s3-website.eu-central-1.amazonaws.com/"]

    resources = [
        ("train-images-idx3-ubyte.gz", "8d4fb7e6c68d591d4c3dfef9ec88bf0d"),
        ("train-labels-idx1-ubyte.gz", "25c81989df183df01b3e8a0aad5dffbe"),
        ("t10k-images-idx3-ubyte.gz", "bef4ecab320f06d8554ea6380940ec79"),
        ("t10k-labels-idx1-ubyte.gz", "bb300cfdad3c16e7a12a480ee83cd310"),
    ]
    classes = ["T-shirt/top", "Trouser", "Pullover", "Dress", "Coat", "Sandal", "Shirt", "Sneaker", "Bag", "Ankle boot"]

    training_file = 'training.pt'
    test_file = 'test.pt'


    def __init__(self, indexes, root: str, normal_class,
            task, data_path,
            download_data = False,
    ) -> None:
        super().__init__()
        self.task = task  # training set or test set
        self.data_path = data_path
        self.indexes = indexes
        self.normal_class = normal_class
        self.download_data = download_data



        if self.download_data:
            self.download()

        if not self._check_exists():
            raise RuntimeError('Dataset not found.' +
                               ' You can use download=True to download it')

        self.data, self.targets = self._load_data()

        if self.indexes != []: #if indexes is equal to [], original labels are not modified as this dataloader object is used by the 'create_reference' function. This function requires the original labels
          self.targets[self.targets != normal_class] = -1
          self.targets[self.targets == normal_class] = -2
          self.targets[self.targets == -2] = 0
          self.targets[self.targets == -1] = 1


    def get_int(self, b: bytes) -> int:
        return int(codecs.encode(b, 'hex'), 16)

    def read_sn3_pascalvincent_tensor(self, path: str, strict: bool = True) -> torch.Tensor:
        """Read a SN3 file in "Pascal Vincent" format (Lush file 'libidx/idx-io.lsh').
           Argument may be a filename, compressed filename, or file object.
        """
        # read
        SN3_PASCALVINCENT_TYPEMAP = {
        8: (torch.uint8, np.uint8, np.uint8),
        9: (torch.int8, np.int8, np.int8),
        11: (torch.int16, np.dtype('>i2'), 'i2'),
        12: (torch.int32, np.dtype('>i4'), 'i4'),
        13: (torch.float32, np.dtype('>f4'), 'f4'),
        14: (torch.float64, np.dtype('>f8'), 'f8')
        }

        with open(path, "rb") as f:
            data = f.read()
        # parse
        magic = self.get_int(data[0:4])
        nd = magic % 256
        ty = magic // 256
        assert 1 <= nd <= 3
        assert 8 <= ty <= 14
        m = SN3_PASCALVINCENT_TYPEMAP[ty]
        s = [self.get_int(data[4 * (i + 1): 4 * (i + 2)]) for i in range(nd)]
        parsed = np.frombuffer(data, dtype=m[1], offset=(4 * (nd + 1)))
        assert parsed.shape[0] == np.prod(s) or not strict
        return torch.from_numpy(parsed.astype(m[2])).view(*s)

    def read_image_file(self, path: str) -> torch.Tensor:
        x = self.read_sn3_pascalvincent_tensor(path, strict=False)
        assert(x.dtype == torch.uint8)
        assert(x.ndimension() == 3)
        return x

    def read_label_file(self, path: str) -> torch.Tensor:
        x = self.read_sn3_pascalvincent_tensor(path, strict=False)
        assert(x.dtype == torch.uint8)
        assert(x.ndimension() == 1)
        return x.long()




    def _load_data(self):
        if (self.task == 'train') | (self.task == 'validate'):
            image_file = "train-images-idx3-ubyte"
            data = self.read_image_file(os.path.join(self.data_path, image_file))
            label_file = "train-labels-idx1-ubyte"
            targets = self.read_label_file(os.path.join(self.data_path, label_file))

            if (self.task == 'train') & (self.indexes != []):
                data = data[self.indexes]
                targets = targets[self.indexes]
            elif self.task == 'validate':
                lst = list(range(0,len(data) ))
                ind = [x for i,x in enumerate(lst) if i not in self.indexes]
                random.seed(1)
                randomlist = random.sample(range(0, len(ind)), 1500)
                data = data[randomlist]
                targets = targets[randomlist]
        else:
            image_file = "t10k-images-idx3-ubyte"
            data = self.read_image_file(os.path.join(self.data_path, image_file))
            label_file = "t10k-labels-idx1-ubyte"
            targets = self.read_label_file(os.path.join(self.data_path, label_file))

        return data, targets


    def __getitem__(self, index: int, seed = 1, base_ind=-1):



        base=False
        img, target = self.data[index], int(self.targets[index])
        img = torch.stack((img,img,img),0)

        if self.task == 'train':
            np.random.seed(seed)
            ind = np.random.randint(len(self.indexes) )
            c=1
            while (ind == index):
                np.random.seed(seed * c)
                ind = np.random.randint(len(self.indexes) )
                c=c+1

            if ind == base_ind:
              base = True

            img2, target2 = self.data[ind], int(self.targets[ind])
            img2 = torch.stack((img2,img2,img2),0)
            label = torch.FloatTensor([0])
        else:
            img2 = torch.Tensor([1])
            label = target



        return img, img2, label, base


    def __len__(self) -> int:
        return len(self.data)

    @property
    def raw_folder(self) -> str:
        return os.path.join(self.root, self.__class__.__name__, 'raw')

    @property
    def processed_folder(self) -> str:
        return os.path.join(self.root, self.__class__.__name__, 'processed')

    @property
    def class_to_idx(self):
        return {_class: i for i, _class in enumerate(self.classes)}

    def _check_exists(self) -> bool:
        return all(
            check_integrity(os.path.join(self.data_path, os.path.splitext(os.path.basename(url))[0]))
            for url, _ in self.resources
        )

    def download(self) -> None:
        """Download the MNIST data if it doesn't exist already."""

        if self._check_exists():
            return

        os.makedirs('./data/', exist_ok=True)

        # download files
        for filename, md5 in self.resources:
            for mirror in self.mirrors:
                url = "{}{}".format(mirror, filename)
                try:
                    print("Downloading {}".format(url))
                    download_and_extract_archive(
                        url, download_root=self.data_path,
                        filename=filename,
                        md5=md5
                    )
                except URLError as error:
                    print(
                        "Failed to download (trying next):\n{}".format(error)
                    )
                    continue
                finally:
                    print()
                break
            else:
                raise RuntimeError("Error downloading {}".format(filename))

    def extra_repr(self) -> str:
        return "Split: {}".format("Train" if self.task == 0 else "Test")
