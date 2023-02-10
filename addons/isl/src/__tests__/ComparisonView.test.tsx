import platform from '../platform';
jest.mock('../platform');
diff --git deletedFile.txt deletedFile.txt
deleted file mode 100644
diff --git newFile.txt newFile.txt
new file mode 100644
diff --git someFile.txt someFile.txt
diff --git -r a1b2c3d4e5f6 some/path/foo.go
--- some/path/foo.go
+++ some/path/foo.go
@@ -0,1 +0,1 @@
-println("hi")
+fmt.Println("hi")

  it('copies file path on click', async () => {
    await openUncommittedChangesComparison();

    // Click on the "foo.go" of "some/path/foo.go".
    act(() => {
      fireEvent.click(inComparisonView().getByText('foo.go'));
    });
    expect(platform.clipboardCopy).toHaveBeenCalledTimes(1);
    expect(platform.clipboardCopy).toHaveBeenCalledWith('foo.go');

    // Click on the "some/" of "some/path/foo.go".
    act(() => {
      fireEvent.click(inComparisonView().getByText('some/'));
    });
    expect(platform.clipboardCopy).toHaveBeenCalledTimes(2);
    expect(platform.clipboardCopy).toHaveBeenLastCalledWith('some/path/foo.go');
  });