import { mount } from '@vue/test-utils';
import SupplementaryList from '../supplementaryLists/SupplementaryList';
import SupplementaryItem from '../supplementaryLists/SupplementaryItem';
import store from '../../../store';
import Uploader from 'shared/views/files/Uploader';

const testNodeId = 'testnode';
const testFile = { id: 'file-1', language: { id: 'en' }, preset: { id: 'video_subtitle' } };

function makeWrapper() {
  return mount(SupplementaryList, {
    store,
    attachToDocument: true,
    propsData: {
      nodeId: testNodeId,
      presetID: 'video_subtitle',
    },
    computed: {
      node() {
        return {
          files: ['file-1', 'file-2'],
        };
      },
      getContentNodeFiles() {
        return () => {
          return [testFile, { id: 'file-2', language: {}, preset: { id: 'high_res_video' } }];
        };
      },
    },
    stubs: {
      SupplementaryItem: true,
    },
  });
}

describe('supplementaryList', () => {
  let wrapper;
  beforeEach(() => {
    wrapper = makeWrapper();
  });
  it('files should filter files based on presetID', () => {
    expect(wrapper.vm.files).toHaveLength(1);
    expect(wrapper.vm.files[0].id).toBe('file-1');
  });
  it('currentLanguages should reflect languages that have been selected', () => {
    expect(wrapper.vm.currentLanguages).toHaveLength(1);
    expect(wrapper.vm.currentLanguages[0]).toBe('en');
  });
  it('readonly should disable uploading', () => {
    wrapper.setProps({ readonly: true });
    expect(wrapper.find('[data-test="add-file"]').exists()).toBe(false);
  });
  describe('methods', () => {
    it('emitted remove event from list item should call deleteFile action', () => {
      let deleteFile = jest.fn();
      wrapper.setMethods({ deleteFile });
      let listItem = wrapper.find(SupplementaryItem);
      listItem.vm.$emit('remove', 'test');
      expect(deleteFile).toHaveBeenCalled();
      expect(deleteFile.mock.calls[0][0]).toEqual(testFile);
    });
    it('emitted uploading event should call createFile action', () => {
      let createFile = jest.fn();
      wrapper.setMethods({ createFile });

      let listItem = wrapper.find(SupplementaryItem);
      let replacementFile = { id: 'replacementFile', language: 'en-PT' };
      listItem.vm.$emit('uploading', replacementFile);

      expect(createFile).toHaveBeenCalled();
      expect(createFile.mock.calls[0][0].id).toBe(replacementFile.id);
      expect(createFile.mock.calls[0][0].language).toBe('en-PT');
    });
    it('emitted uploading event from Uploader should call createFile', () => {
      let uploadFile = { id: 'filetest' };
      let createFile = jest.fn();
      let uploader = wrapper.find(Uploader);

      wrapper.setMethods({ createFile });
      wrapper.setData({ selectedLanguage: 'en-PT' });

      uploader.vm.$emit('uploading', [uploadFile]);

      expect(createFile).toHaveBeenCalled();
      expect(createFile.mock.calls[0][0].id).toBe(uploadFile.id);
      expect(createFile.mock.calls[0][0].language).toBe('en-PT');
    });
  });
  describe('uploading workflow', () => {
    it('clicking add file link should enable language selection', () => {
      wrapper.find('[data-test="add-file"]').trigger('click');
      expect(wrapper.find('[data-test="select-language"]').exists()).toBe(true);
    });
    it('selecting a language should enable file uploading', () => {
      wrapper.setData({ selectedLanguage: 'en' });
      expect(wrapper.find('[data-test="upload-file"]').exists()).toBe(true);
    });
  });
});
